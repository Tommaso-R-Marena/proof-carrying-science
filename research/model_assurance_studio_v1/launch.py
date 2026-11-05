"""Launch local PCS Studio and open its interface in the default browser."""
import threading
import webbrowser
import uvicorn

URL='http://127.0.0.1:8765'
if __name__=='__main__':
    print('PCS Model Assurance Studio:', URL)
    print('Local-only; no artifact persistence; model code never executed.')
    print('Press Ctrl+C to close the local service.')
    timer=threading.Timer(1.5,lambda:webbrowser.open(URL))
    timer.daemon=True
    timer.start()
    uvicorn.run('studio.server:app',host='127.0.0.1',port=8765,log_level='warning')
