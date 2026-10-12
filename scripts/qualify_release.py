"""Run only reviewed local qualification recipes; no production authority."""
from pcs.release_qualification_v1 import main
if __name__ == '__main__':
    raise SystemExit(main())
