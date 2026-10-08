"""One child at a time, hard wall limits for native preparation and conversion."""
import json
import os
import select
import signal
import time


class PhaseError(ValueError): pass


def isolated(function, seconds):
    reader, writer = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(reader)
        try:
            try: payload = {'ok': function()}
            except BaseException as exc: payload = {'error': type(exc).__name__ + ':' + str(exc)[:1200]}
            data = json.dumps(payload).encode()
            while data:
                count = os.write(writer, data[:65536]); data = data[count:]
            os.close(writer)
            os._exit(0)
        except BaseException: os._exit(70)
    os.close(writer)
    chunks = []; total = 0; status = None; deadline = time.monotonic() + seconds
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                os.kill(pid, signal.SIGKILL); _, status = os.waitpid(pid, 0)
                raise PhaseError('phase:hard_timeout')
            ready, _, _ = select.select([reader], [], [], min(left, .2))
            if ready:
                data = os.read(reader, 65536)
                if not data: break
                total += len(data)
                if total > 32 * 1024 * 1024: raise PhaseError('phase:output_limit')
                chunks.append(data)
        _, status = os.waitpid(pid, 0)
        if status != 0: raise PhaseError('phase:child_exit:' + str(os.waitstatus_to_exitcode(status)))
        try: payload = json.loads(b''.join(chunks))
        except Exception as exc: raise PhaseError('phase:invalid_response') from exc
        if 'error' in payload: raise PhaseError(payload['error'])
        return payload['ok']
    finally:
        os.close(reader)
        if status is None:
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
            os.waitpid(pid, 0)
