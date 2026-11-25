//! Bounded OpenAI-compatible SSE reader for plain answers only.
//! Partial text is never a completed answer or an action.
use anyhow::{bail, ensure, Result};
use serde_json::Value;
use std::io::{BufRead, BufReader, Read};

const WIRE_LIMIT:u64=2*1024*1024;
const LINE_LIMIT:usize=64*1024;
const ANSWER_LIMIT:usize=64*1024;

pub fn read_answer(source:impl Read,mut emit:impl FnMut(&str)->Result<()>) -> Result<String> {
    let mut reader=BufReader::new(source.take(WIRE_LIMIT+1));
    let mut line=Vec::new();
    let mut wire=0usize;
    let mut answer=String::new();
    let mut finished=false;
    let mut data=String::new();
    loop {
        line.clear();
        // Bound a single line before allocating arbitrary server data.
        let n=reader.by_ref().take((LINE_LIMIT+1) as u64).read_until(b'\n',&mut line)?;
        ensure!(n>0,"Stream ended before completion");
        wire+=n;
        ensure!(wire as u64<=WIRE_LIMIT && n<=LINE_LIMIT,"Stream budget exceeded");
        let text=std::str::from_utf8(&line)?.trim_end_matches(['\r','\n']);
        if let Some(value)=text.strip_prefix("data:") {
            let value=value.strip_prefix(' ').unwrap_or(value);
            if !data.is_empty(){data.push('\n');}
            ensure!(data.len()+value.len()<=LINE_LIMIT,"Oversized stream event");
            data.push_str(value);
        } else if text.is_empty() {
            if data.is_empty(){continue;}
            if data=="[DONE]" {
                ensure!(finished && !answer.trim().is_empty(),"Incomplete stream");
                return Ok(answer);
            }
            let event:Value=serde_json::from_str(&data).map_err(|_|anyhow::anyhow!("Malformed stream event"))?;
            data.clear();
            ensure!(event.get("error").is_none(),"Server stream error");
            let choices=event["choices"].as_array().ok_or_else(||anyhow::anyhow!("Missing stream choices"))?;
            if choices.is_empty(){continue;} // optional usage-only event
            ensure!(choices.len()==1 && !finished,"Unexpected stream choice");
            let choice=&choices[0];
            ensure!(choice["index"].as_u64()==Some(0),"Invalid stream choice index");
            let delta=choice["delta"].as_object().ok_or_else(||anyhow::anyhow!("Missing delta"))?;
            ensure!(delta.get("role").is_none_or(|v|v.as_str()==Some("assistant")),"Invalid stream role");
            ensure!(delta.get("tool_calls").is_none_or(Value::is_null)&&delta.get("function_call").is_none_or(Value::is_null),"Unexpected streamed action");
            if let Some(content)=delta.get("content").filter(|v|!v.is_null()){
                let token=content.as_str().ok_or_else(||anyhow::anyhow!("Invalid stream content"))?;
                ensure!(answer.len()+token.len()<=ANSWER_LIMIT,"Answer budget exceeded");
                // Caller may return an error to stop consuming the connection.
                // This is cooperative cancellation at received chunk boundaries.
                emit(token)?;
                answer.push_str(token);
            }
            if let Some(reason)=choice.get("finish_reason").filter(|v|!v.is_null()){
                ensure!(reason.as_str()==Some("stop"),"Incomplete streamed answer");
                finished=true;
            }
        } else if text.starts_with(':') || text.starts_with("event:") || text.starts_with("id:") || text.starts_with("retry:") {
            continue;
        } else {
            bail!("Unexpected stream framing");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    const FIRST:&str="data: {\"choices\":[{\"index\":0,\"delta\":{\"role\":\"assistant\",\"content\":\"hello \"},\"finish_reason\":null}]}\r\n\r\n";
    const SECOND:&str="data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"world\"},\"finish_reason\":null}]}\n\n";
    const FINISH:&str="data: {\"choices\":[{\"index\":0,\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n";
    #[test]
    fn chunks_and_complete_answer_agree(){
        let input=format!("{FIRST}{SECOND}{FINISH}data: [DONE]\n\n");
        let mut seen=Vec::new();
        let answer=read_answer(input.as_bytes(),|s|{seen.push(s.to_owned());Ok(())}).unwrap();
        assert_eq!(seen,["hello ","world"]);
        assert_eq!(answer,"hello world");
    }
    #[test]
    fn truncated_or_action_streams_fail(){
        for input in [FIRST.to_owned(),format!("{FIRST}data: [DONE]\n\n"),
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"tool_calls\":[{}]}}]}\n\n".into(),
            format!("{FIRST}{}",FINISH.replace("stop","length")),
            format!("data: {}\n\n","x".repeat(LINE_LIMIT))]{
            assert!(read_answer(input.as_bytes(),|_|Ok(())).is_err());
        }
    }
    #[test]
    fn consumer_can_stop_at_first_chunk(){
        let input=format!("{FIRST}{SECOND}{FINISH}data: [DONE]\n\n");
        let mut calls=0;
        assert!(read_answer(input.as_bytes(),|_|{calls+=1;bail!("cancelled")}).is_err());
        assert_eq!(calls,1);
    }
}
