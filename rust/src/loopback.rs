//! Narrow non-streaming authenticated loopback HTTP transport.
//! Connect first, verify the server-side tuple, then send secrets on that
//! very socket. No DNS, proxy, redirects, reuse, retries or chunked decoding.
use crate::process::Owned;
use anyhow::{bail, ensure, Result};
use serde_json::Value;
use std::{io::{Read,Write},net::{Ipv4Addr,SocketAddrV4,TcpStream},thread,time::{Duration,Instant}};

const HEADER_MAX:usize=32*1024;
const BODY_MAX:usize=2*1024*1024;
const REQUEST_MAX:usize=256*1024;
#[derive(Clone,Copy)]
pub(crate) enum Endpoint { Props, Models, Completion }
impl Endpoint {
    fn path(self)->&'static str {match self {
        Self::Props=>"/props",Self::Models=>"/v1/models",Self::Completion=>"/v1/chat/completions"
    }}
    fn method(self)->&'static str {if matches!(self,Self::Completion){"POST"}else{"GET"}}
}
fn remaining(deadline:Instant)->Result<Duration>{
    let value=deadline.saturating_duration_since(Instant::now());
    ensure!(!value.is_zero(),"Local request timed out");
    Ok(value)
}
fn parse_header(header:&[u8])->Result<(u16,usize)>{
    ensure!(header.is_ascii(),"Non-ASCII HTTP header");
    let text=std::str::from_utf8(header)?;
    let mut lines=text.split("\r\n");
    let status=lines.next().ok_or_else(||anyhow::anyhow!("Missing HTTP status"))?;
    let mut parts=status.splitn(3,' ');
    ensure!(matches!(parts.next(),Some("HTTP/1.1"|"HTTP/1.0")),"Invalid HTTP version");
    let code=parts.next().ok_or_else(||anyhow::anyhow!("Missing HTTP status"))?;
    ensure!(code.len()==3&&code.bytes().all(|b|b.is_ascii_digit()),"Invalid HTTP status");
    let code:u16=code.parse()?;
    ensure!((200..600).contains(&code),"Unsupported HTTP status");
    let mut length=None;
    let mut content_type=None;
    for line in lines{
        ensure!(!line.is_empty(),"Unexpected empty header");
        let (name,value)=line.split_once(':').ok_or_else(||anyhow::anyhow!("Malformed HTTP header"))?;
        ensure!(!name.is_empty()&&name.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'-'),"Invalid HTTP header name");
        let value=value.trim_matches([' ','\t']);
        ensure!(value.bytes().all(|b| b==b'\t'||(32..=126).contains(&b)),"Invalid HTTP header value");
        match name.to_ascii_lowercase().as_str(){
            "content-length"=>{
                ensure!(length.is_none()&&!value.is_empty()&&value.bytes().all(|b|b.is_ascii_digit()),"Ambiguous response length");
                let n:usize=value.parse()?;
                ensure!(n<=BODY_MAX,"Response too large");
                length=Some(n);
            }
            "content-type"=>{
                ensure!(content_type.is_none(),"Duplicate content type");
                content_type=Some(value.split(';').next().unwrap_or("").trim().to_ascii_lowercase());
            }
            "transfer-encoding"=>bail!("Unsupported transfer encoding"),
            "content-encoding"=>ensure!(value.eq_ignore_ascii_case("identity"),"Unsupported content encoding"),
            _=>{}
        }
    }
    let length=length.ok_or_else(||anyhow::anyhow!("Missing response length"))?;
    if code==200 {ensure!(content_type.as_deref()==Some("application/json"),"Expected JSON response");}
    Ok((code,length))
}
fn read_response(socket:&mut TcpStream,deadline:Instant)->Result<Value>{
    let mut wire=Vec::new();
    let mut buffer=[0u8;8192];
    let boundary=loop{
        if let Some(i)=wire.windows(4).position(|x|x==b"\r\n\r\n"){
            ensure!(i<=HEADER_MAX,"HTTP header too large");
            break i;
        }
        ensure!(wire.len()<=HEADER_MAX,"HTTP header too large");
        socket.set_read_timeout(Some(remaining(deadline)?))?;
        let n=socket.read(&mut buffer)?;
        ensure!(n>0,"Incomplete HTTP header");
        wire.extend_from_slice(&buffer[..n]);
    };
    let (status,length)=parse_header(&wire[..boundary])?;
    ensure!(status==200,"Model HTTP status {status}");
    let mut body=wire.split_off(boundary+4);
    ensure!(body.len()<=length,"Unexpected extra HTTP body bytes");
    while body.len()<length{
        socket.set_read_timeout(Some(remaining(deadline)?))?;
        let want=(length-body.len()).min(buffer.len());
        let n=socket.read(&mut buffer[..want])?;
        ensure!(n>0,"Incomplete HTTP body");
        body.extend_from_slice(&buffer[..n]);
    }
    serde_json::from_slice(&body).map_err(|_|anyhow::anyhow!("Invalid server JSON"))
}

pub(crate) fn authorized(child:&Owned,port:u16,key:&str,endpoint:Endpoint,payload:Option<&Value>,timeout:Duration)->Result<Value>{
    ensure!(!key.is_empty()&&key.len()<=128&&key.bytes().all(|b|b.is_ascii_alphanumeric()),"Invalid runtime credential");
    ensure!(matches!(endpoint,Endpoint::Completion)==payload.is_some(),"Invalid request body");
    let body=payload.map(serde_json::to_vec).transpose()?.unwrap_or_default();
    ensure!(body.len()<=REQUEST_MAX,"Request too large");
    let deadline=Instant::now()+timeout;
    let address=SocketAddrV4::new(Ipv4Addr::LOCALHOST,port);
    let mut socket=TcpStream::connect_timeout(&address.into(),remaining(deadline)?.min(Duration::from_secs(2)))?;
    // Server-side inode may be assigned only when accept() completes.
    // Never send the key while a connection is pending or owned by a foreign process.
    let ownership_deadline=Instant::now()+remaining(deadline)?.min(Duration::from_secs(2));
    loop{
        if child.connection_owned(&socket)? {break;}
        ensure!(Instant::now()<ownership_deadline,"Connected peer ownership not verified");
        thread::sleep(Duration::from_millis(20));
    }
    socket.set_write_timeout(Some(remaining(deadline)?))?;
    let header=format!("{} {} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {key}\r\nAccept: application/json\r\nAccept-Encoding: identity\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",endpoint.method(),endpoint.path(),body.len());
    socket.write_all(header.as_bytes())?;
    socket.set_write_timeout(Some(remaining(deadline)?))?;
    socket.write_all(&body)?;
    read_response(&mut socket,deadline)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strict_framing(){
        let header=b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2";
        assert_eq!(parse_header(header).unwrap(),(200,2));
        for bad in [
            "HTTP/1.1 200 OK\r\nContent-Type: application/json",
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\ncontent-length: 2",
            "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Length: 2",
            "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 2",
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 99999999",
        ]{assert!(parse_header(bad.as_bytes()).is_err());}
    }
    #[test]
    fn exact_response_bytes_and_truncation(){
        use std::net::TcpListener;
        for (response,good) in [
            ("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}",true),
            ("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 3\r\n\r\n{}",false),
        ]{
            let l=TcpListener::bind(("127.0.0.1",0)).unwrap();
            let addr=l.local_addr().unwrap();
            let t=thread::spawn(move||{let(mut c,_)=l.accept().unwrap();c.write_all(response.as_bytes()).unwrap();});
            let mut c=TcpStream::connect(addr).unwrap();
            assert_eq!(read_response(&mut c,Instant::now()+Duration::from_secs(2)).is_ok(),good);
            t.join().unwrap();
        }
    }
}
