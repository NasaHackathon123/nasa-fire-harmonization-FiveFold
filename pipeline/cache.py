"""Private, explicit explorer-cache retention operation: python -m pipeline.cache."""
import json


def main():
    # Local CLI authorization is the operator's filesystem/process access.
    # FastAPI dependencies apply only to HTTP requests.
    from backend.app.routers.explorer import cleanup
    print(json.dumps(cleanup()))


if __name__ == '__main__':
    main()
