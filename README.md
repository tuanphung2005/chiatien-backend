# ChiaTien Python Backend

Expense sharing API with PaddleOCR receipt scanning.

## Requirements

- Python 3.10+ (3.12 recommended)
- PostgreSQL database
- WSL2 (for Windows users)

## Setup (WSL)

```bash
cd /mnt/c/Users/tuan2/coding/chiatien-rn/python

# Create virtual environment (if not exists)
python3 -m venv venv

# Install dependencies
./venv/bin/pip install fastapi uvicorn prisma python-jose passlib bcrypt cloudinary exponent-server-sdk python-multipart python-dotenv pydantic pydantic-settings paddlepaddle paddleocr

# Generate Prisma client
export PATH="./venv/bin:$PATH"
prisma generate

# Run the server
DISABLE_MODEL_SOURCE_CHECK=True ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

## PostgreSQL Configuration for WSL

If running the Python backend in WSL and PostgreSQL on Windows, you need to:

1. **Find Windows host IP** (run in WSL):
   ```bash
   ip route | grep default | awk '{print $3}'
   ```

2. **Update `.env`** with the Windows IP:
   ```
   DATABASE_URL="postgresql://postgres:1@<WINDOWS_IP>:5432/chiatien?schema=public"
   ```

3. **Configure PostgreSQL to accept remote connections**:
   
   Edit `postgresql.conf` (usually in PostgreSQL data directory):
   ```
   listen_addresses = '*'
   ```
   
   Edit `pg_hba.conf` to allow connections from WSL subnet:
   ```
   host    all    all    172.0.0.0/8    md5
   ```
   
   Then restart PostgreSQL service.

4. **Allow PostgreSQL through Windows Firewall**:
   - Open Windows Defender Firewall
   - Allow port 5432 for inbound connections

# main setup for dev env

1. Set up PostgreSQL database and user
bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '1';"
sudo -u postgres createdb chiatien
2. Navigate to the Python backend and create virtual environment
bash
cd /mnt/c/Users/tuan2/coding/chiatien-rn/python
python3 -m venv venv
source venv/bin/activate
3. Install dependencies
bash
pip install -r requirements.txt
4. Generate Prisma client and push schema
bash
prisma generate
prisma db push
5. Run the backend
bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

## API Endpoints

### Auth
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register

### Groups
- `GET /api/groups` - List user's groups
- `POST /api/groups` - Create group
- `GET /api/groups/{id}` - Get group details
- `PUT /api/groups/{id}` - Update group
- `DELETE /api/groups/{id}` - Delete group

### Expenses
- `GET /api/expenses` - List expenses
- `POST /api/expenses` - Create expense
- `DELETE /api/expenses/{id}` - Delete expense
- `PATCH /api/expenses/{id}` - Settle expense

### Receipts
- `POST /api/receipts/parse` - Parse receipt with PaddleOCR

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## PaddleOCR

The first time you parse a receipt, PaddleOCR will download Vietnamese language models (~500MB). This happens automatically.

If PaddleOCR is not available (e.g., unsupported Python version), the API will fall back to mock data for testing purposes.

## Frontend Configuration

Update the frontend `.env` to point to the Python backend:

```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

For Android emulator, use `10.0.2.2:8000`. For physical devices, use your machine's LAN IP.

# portfowarding

hostname -I | awk '{print $1}
172.25.186.242

PS C:\Users\tuan2> netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$(wsl hostname -I)                                                                                                                                                                                                                        PS C:\Users\tuan2> netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=172.25.186.242                                                                                                                                                                                                                            PS C:\Users\tuan2> netsh advfirewall firewall add rule name="Python Backend 8000" dir=in action=allow protocol=TCP localport=8000                                                                                                               Ok.         