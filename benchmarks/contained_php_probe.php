<?php

declare(strict_types=1);

// Install this entry point in the reviewed, pinned image at /tinybuilder/probe.php.
$request = json_decode(file_get_contents('php://stdin'), true, 64, JSON_THROW_ON_ERROR);
$observe = require '/fixture/probe_entry.php';
if (!is_callable($observe)) {
    throw new RuntimeException('Fixture bridge must return an observation callback');
}
echo json_encode($observe($request), JSON_THROW_ON_ERROR);
