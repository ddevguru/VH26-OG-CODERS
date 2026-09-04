# LeakGuard Ecosystem & Resource Lifecycle Patterns

This document details the Python ecosystem libraries, database drivers, HTTP clients, and web framework patterns supported by LeakGuard static analysis rules.

---

## 1. Standard Library Resource Patterns

### Supported Standard Library Modules
| Module | Acquisition Patterns | Release Methods | Support Level |
| :--- | :--- | :--- | :--- |
| `io` | `open`, `io.open`, `io.FileIO`, `io.TextIOWrapper`, `io.BufferedWriter`, `io.BufferedReader`, `io.BytesIO`, `io.StringIO` | `close`, `detach`, `flush` | **Full** |
| `pathlib` | `Path.open`, `pathlib.Path.open` | `close` | **Full** |
| `socket` | `socket.socket`, `socket.create_connection`, `socket.fromfd`, `socket.socketpair` | `close`, `shutdown` | **Full** |
| `sqlite3` | `sqlite3.connect`, `conn.cursor()` | `close` | **Full** |
| `tempfile` | `tempfile.NamedTemporaryFile`, `tempfile.TemporaryDirectory`, `tempfile.SpooledTemporaryFile`, `tempfile.mkstemp` | `close`, `cleanup` | **Full** |
| `subprocess` | `subprocess.Popen`, `Popen` | `close`, `wait`, `terminate`, `kill` | **Full** |
| `threading` | `threading.Lock`, `threading.RLock`, `threading.Semaphore`, `threading.BoundedSemaphore` | `release` | **Full** |
| `asyncio` | `asyncio.Lock`, `asyncio.Semaphore`, `asyncio.BoundedSemaphore`, `asyncio.open_connection`, `asyncio.start_server` | `release`, `close` | **Full** |
| `selectors` | `selectors.DefaultSelector`, `selectors.SelectSelector`, `selectors.PollSelector`, `selectors.KqueueSelector`, `selectors.EpollSelector` | `close`, `unregister` | **Full** |
| `logging` | `logging.FileHandler`, `logging.handlers.RotatingFileHandler`, `logging.handlers.TimedRotatingFileHandler`, `logging.handlers.SocketHandler` | `close` | **Full** |

---

## 2. Database Drivers & ORM Patterns

### Supported Drivers
- **DB-API 2.0 Drivers**: `sqlite3`, `psycopg2.connect`, `pymysql.connect`, `asyncpg.connect`, `mariadb.connect`, `mysql.connector.connect`, `cx_Oracle.connect`.
- **SQLAlchemy**: `create_engine`, `Engine.connect`, `Session`, `sessionmaker`, `SessionLocal`.

### Lifecycle Modeling
- **Connection Handles**: Tracked from `connect()` call until `close()`, `disconnect()`, or `dispose()`.
- **Cursors**: Tracked from `conn.cursor()` until `cur.close()`. Closing a parent connection implicitly releases dependent child resources.

---

## 3. HTTP Client Patterns

### Supported HTTP Clients
- **`requests`**: `requests.Session()`, `requests.get()`, `requests.post()`, `requests.put()`, `requests.delete()`.
- **`httpx`**: `httpx.Client()`, `httpx.AsyncClient()`.
- **`aiohttp`**: `aiohttp.ClientSession()`, `aiohttp.TCPConnector()`.
- **`urllib.request`**: `urllib.request.urlopen()`.

### Lifecycle Modeling
- Context manager `with` and `async with` blocks guarantee `SAFE` state.
- Explicit `.close()` or `.aclose()` calls on session handles are tracked path-sensitively across branches and exceptions.

---

## 4. Web Framework Patterns

### Supported Patterns
- **FastAPI**: Yield dependencies (`def get_db(): db = SessionLocal(); try: yield db; finally: db.close()`).
- **Flask**: App context teardown functions (`@app.teardown_appcontext def cleanup(exception): g.db.close()`).
- **Django**: Explicit database connection cleanup (`django.db.connection.close()`).

---

## 5. Non-Supported & Boundary Conditions

To maintain precision and prevent false positives:
1. **Dynamic Execution**: `eval()`, `exec()`, or dynamic `getattr()` calls are out of scope for static analysis.
2. **Implicit Global Garbage Collection**: Code relying solely on Python CPython refcounting (`__del__`) without explicit context managers or `.close()` calls is flagged as `POTENTIAL_LEAK` or `DEFINITE_LEAK`.
3. **Unknown Third-Party Libraries**: Unrecognized functions returning resources produce `UNKNOWN` or `POTENTIAL_LEAK` findings rather than false `DEFINITE_LEAK` alerts.
