# Knowledge Graph Database Deployment

PostgreSQL + pgvector for persistent knowledge graph storage.

## Quick Start (Home Server)

```bash
# 1. Set a secure password
export KNOWLEDGE_DB_PASSWORD="your-secure-password"

# 2. Run setup
./setup.sh

# 3. Note your server's IP address
ip addr show | grep "inet "
```

## Client Configuration (Laptop/PC)

Create `.env` file in your project:

```bash
KNOWLEDGE_BACKEND=postgres
KNOWLEDGE_DB_HOST=192.168.1.100  # Your server IP
KNOWLEDGE_DB_PORT=5432
KNOWLEDGE_DB_NAME=knowledge_graph
KNOWLEDGE_DB_USER=knowledge
KNOWLEDGE_DB_PASSWORD=your-secure-password
```

Or set environment variables before running Claude Code.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│     Laptop      │     │    Home PC      │
│  Claude Code    │────▶│   PostgreSQL    │
│  + MCP Server   │     │   + pgvector    │
└─────────────────┘     └─────────────────┘
        │                       │
        └───────────────────────┘
              Local Network
```

## Files

- `docker-compose.yml` - Container definitions
- `schema.sql` - Database schema with tables and indexes
- `pg_hba.conf` - Authentication rules for remote access
- `setup.sh` - Automated setup script

## Management

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f db

# Connect to database
docker compose exec db psql -U knowledge -d knowledge_graph

# Backup
docker compose exec db pg_dump -U knowledge knowledge_graph > backup.sql

# Restore
docker compose exec -T db psql -U knowledge -d knowledge_graph < backup.sql
```

## Optional: pgAdmin

For database management UI:

```bash
docker compose --profile admin up -d
```

Access at http://localhost:5050 (admin@localhost / admin)

## Troubleshooting

### Can't connect from laptop

1. Check firewall: `sudo ufw allow 5432/tcp`
2. Verify pg_hba.conf includes your network range
3. Test connection: `psql -h <server-ip> -U knowledge -d knowledge_graph`

### Permission denied

Check pg_hba.conf has your IP range and restart:
```bash
docker compose restart db
```

### Vector search not working

Verify pgvector extension:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```
