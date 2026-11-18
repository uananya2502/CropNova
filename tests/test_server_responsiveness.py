"""Real HTTP checks for the freeze reported after adding slow AI calls."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import socket
from threading import Event, Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import patch
from app import create_server
from demo import PRESETS


@contextmanager
def running_server():
    server = create_server(port=0)
    worker = Thread(target=server.serve_forever, kwargs={'poll_interval':0.01}, daemon=True)
    worker.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port), server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_home_page_responds_during_slow_ai_request():
    entered, release = Event(), Event()
    def slow_explanation(report, requested=False):
        entered.set()
        release.wait(timeout=5)
        return {'status':'unavailable','message':'Test service delay','explanations':[]}
    with patch('app.generate_explanation',side_effect=slow_explanation), running_server() as (base, _):
        payload=urlencode({**PRESETS['reference-wheat'][1],'use_genai':'yes'},doseq=True).encode()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(urlopen,Request(base+'/assess',data=payload),timeout=8)
            try:
                assert entered.wait(timeout=2), 'The assessment never reached the AI step.'
                with urlopen(base+'/',timeout=2) as response:
                    assert response.status==200
                assert not release.is_set(), 'Home page must work before AI finishes.'
            finally:
                release.set()
            with pending.result(timeout=3) as response:
                assert response.status==200
                assert b'Options that match your conditions' in response.read()


def test_unused_browser_connection_does_not_block_other_pages():
    with running_server() as (base,port):
        # Browsers may open a spare TCP connection before sending any request.
        with socket.create_connection(('127.0.0.1',port),timeout=2):
            with urlopen(base+'/assess',timeout=2) as response:
                assert response.status==200
