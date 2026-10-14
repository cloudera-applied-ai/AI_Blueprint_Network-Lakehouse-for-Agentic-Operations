#!/bin/bash
#
# PostgreSQL Installation Script for Network Data Lakehouse
# Installs PostgreSQL in user space (no sudo required)
# Downloads binaries if not available
#

set -e  # Exit on error

# Configuration - use environment variables from CML (.project-metadata.yaml), fallback to defaults
DB_NAME="${DB_NAME:-cable_network}"
DB_USER="${DB_USER:-cable_user}"
DB_PASSWORD="${DB_PASSWORD:-cable_secure_pass_2024}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# PostgreSQL version to download if needed
PG_VERSION="16.4"
PG_MAJOR="16"

# Paths - install in user's home directory
PG_HOME="$HOME/.postgres"
PG_DATA="$PG_HOME/data"
PG_LOG="$PG_HOME/postgres.log"
PG_BIN="$PG_HOME/bin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PostgreSQL User-Space Installation${NC}"
echo -e "${GREEN}Network Data Lakehouse${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Add local bin to PATH if it exists
if [ -d "$PG_BIN" ]; then
    export PATH="$PG_BIN:$PATH"
fi

# Check if PostgreSQL binaries are available
# Note: Zonky embedded binaries only include initdb, pg_ctl, and postgres (no psql)
check_postgres_binaries() {
    if command -v initdb &> /dev/null && command -v pg_ctl &> /dev/null && command -v postgres &> /dev/null; then
        return 0
    fi
    # Also check local installation
    if [ -x "$PG_BIN/initdb" ] && [ -x "$PG_BIN/pg_ctl" ] && [ -x "$PG_BIN/postgres" ]; then
        export PATH="$PG_BIN:$PATH"
        return 0
    fi
    return 1
}

# Download and extract PostgreSQL binaries
download_postgres() {
    echo -e "${GREEN}[1/4] Downloading PostgreSQL binaries...${NC}"

    if check_postgres_binaries; then
        echo -e "${GREEN}PostgreSQL binaries already available${NC}"
        return 0
    fi

    mkdir -p "$PG_HOME"
    cd "$PG_HOME"

    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            ARCH_NAME="amd64"
            ZONKY_ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH_NAME="arm64v8"
            ZONKY_ARCH="arm64v8"
            ;;
        *)
            echo -e "${RED}Unsupported architecture: $ARCH${NC}"
            exit 1
            ;;
    esac

    echo -e "${YELLOW}Downloading PostgreSQL $PG_VERSION for $ARCH...${NC}"

    # Primary source: Zonky's embedded-postgres-binaries from Maven
    # These are well-maintained portable Linux builds designed for embedded/containerized use
    DOWNLOAD_URL="https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-${ZONKY_ARCH}/${PG_VERSION}.0/embedded-postgres-binaries-linux-${ZONKY_ARCH}-${PG_VERSION}.0.jar"

    echo -e "${YELLOW}Downloading from: $DOWNLOAD_URL${NC}"

    download_success=false

    if command -v curl &> /dev/null; then
        if curl -fsSL "$DOWNLOAD_URL" -o postgresql.jar; then
            download_success=true
        fi
    elif command -v wget &> /dev/null; then
        if wget -q "$DOWNLOAD_URL" -O postgresql.jar; then
            download_success=true
        fi
    else
        echo -e "${RED}Neither curl nor wget available${NC}"
        exit 1
    fi

    if [ "$download_success" = false ]; then
        echo -e "${RED}Failed to download PostgreSQL binaries${NC}"
        echo -e "${YELLOW}You may need to configure an external PostgreSQL database instead.${NC}"
        exit 1
    fi

    # Extract the JAR (it's just a ZIP file)
    echo -e "${YELLOW}Extracting PostgreSQL binaries...${NC}"

    # Check if unzip is available, if not use jar or python
    if command -v unzip &> /dev/null; then
        unzip -q postgresql.jar "postgres-linux-${ZONKY_ARCH}.txz" -d . 2>/dev/null || \
        unzip -q postgresql.jar -d .
    elif command -v jar &> /dev/null; then
        jar -xf postgresql.jar
    elif command -v python3 &> /dev/null; then
        python3 -c "import zipfile; zipfile.ZipFile('postgresql.jar').extractall('.')"
    else
        echo -e "${RED}No extraction tool available (need unzip, jar, or python3)${NC}"
        exit 1
    fi

    # Find and extract the txz archive
    TXZ_FILE=$(find . -name "postgres-linux-*.txz" -type f 2>/dev/null | head -1)
    if [ -n "$TXZ_FILE" ] && [ -f "$TXZ_FILE" ]; then
        tar -xJf "$TXZ_FILE" 2>/dev/null || tar -xf "$TXZ_FILE"
        rm -f "$TXZ_FILE"
    fi

    # Clean up JAR file
    rm -f postgresql.jar

    # Handle different extracted structures
    if [ -d "pgsql" ]; then
        cp -r pgsql/* . 2>/dev/null || true
        rm -rf pgsql
    fi

    # Ensure bin directory exists and add to PATH
    if [ -d "$PG_BIN" ] && [ -x "$PG_BIN/initdb" ]; then
        export PATH="$PG_BIN:$PATH"
        chmod +x "$PG_BIN"/* 2>/dev/null || true
        echo -e "${GREEN}PostgreSQL binaries installed to $PG_BIN${NC}"
    else
        echo -e "${RED}Failed to install PostgreSQL binaries - bin directory not found${NC}"
        echo -e "${YELLOW}Contents of $PG_HOME:${NC}"
        ls -la "$PG_HOME"
        exit 1
    fi

    cd - > /dev/null
}

# Initialize PostgreSQL data directory
init_database() {
    echo -e "${GREEN}[2/4] Initializing PostgreSQL data directory...${NC}"

    if [ -d "$PG_DATA" ] && [ -f "$PG_DATA/PG_VERSION" ]; then
        echo -e "${YELLOW}Data directory already exists: $PG_DATA${NC}"
        return 0
    fi

    mkdir -p "$PG_HOME"

    # Initialize the database cluster
    initdb -D "$PG_DATA" -U postgres -A trust --encoding=UTF8

    # Configure PostgreSQL for local connections with password auth
    cat >> "$PG_DATA/postgresql.conf" << EOF

# Custom settings for Network Data Lakehouse
listen_addresses = 'localhost'
port = $DB_PORT
unix_socket_directories = '$PG_HOME'
EOF

    # Configure authentication
    cat > "$PG_DATA/pg_hba.conf" << EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                trust
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF

    echo -e "${GREEN}Database initialized at $PG_DATA${NC}"
}

# Start PostgreSQL
start_postgres() {
    echo -e "${GREEN}[4/4] Starting PostgreSQL...${NC}"

    # Check if already running
    if pg_ctl -D "$PG_DATA" status > /dev/null 2>&1; then
        echo -e "${YELLOW}PostgreSQL is already running${NC}"
        return 0
    fi

    pg_ctl -D "$PG_DATA" -l "$PG_LOG" -o "-k $PG_HOME" start

    # Wait for PostgreSQL to be ready
    for i in {1..10}; do
        if pg_ctl -D "$PG_DATA" status > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    if pg_ctl -D "$PG_DATA" status > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL started successfully${NC}"
    else
        echo -e "${RED}Failed to start PostgreSQL. Check log: $PG_LOG${NC}"
        cat "$PG_LOG"
        exit 1
    fi
}

# Create database and user using single-user mode
# Zonky embedded binaries do not include psql, so we use postgres --single
setup_database() {
    echo -e "${GREEN}[3/4] Creating database and user...${NC}"

    # Single-user mode requires the server to be stopped
    pg_ctl -D "$PG_DATA" stop 2>/dev/null || true
    sleep 1
    rm -f "$PG_DATA/postmaster.pid"

    # Create user (ignore error if already exists)
    echo "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" | \
        postgres --single -D "$PG_DATA" postgres 2>&1 && \
        echo -e "${GREEN}User $DB_USER created${NC}" || \
        echo -e "${YELLOW}User $DB_USER may already exist${NC}"

    # Ensure password is current
    echo "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" | \
        postgres --single -D "$PG_DATA" postgres 2>&1 || true

    # Create database (ignore error if already exists)
    echo "CREATE DATABASE $DB_NAME OWNER $DB_USER;" | \
        postgres --single -D "$PG_DATA" postgres 2>&1 && \
        echo -e "${GREEN}Database $DB_NAME created${NC}" || \
        echo -e "${YELLOW}Database $DB_NAME may already exist${NC}"

    # Grant privileges on public schema
    echo "GRANT ALL ON SCHEMA public TO $DB_USER;" | \
        postgres --single -D "$PG_DATA" "$DB_NAME" 2>&1 && \
        echo -e "${GREEN}Privileges granted${NC}" || \
        echo -e "${YELLOW}Could not grant schema privileges (may already be set)${NC}"

    echo -e "${GREEN}Database setup complete${NC}"
}


# Test connection
test_connection() {
    echo ""
    echo -e "${GREEN}Testing database connection...${NC}"

    if pg_ctl -D "$PG_DATA" status > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL is running and ready${NC}"
    else
        echo -e "${YELLOW}PostgreSQL may not be running. Check $PG_LOG for details.${NC}"
    fi
}

# Main
main() {
    download_postgres
    init_database
    setup_database
    start_postgres
    test_connection

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "PostgreSQL binaries: ${YELLOW}$PG_BIN${NC}"
    echo -e "PostgreSQL data: ${YELLOW}$PG_DATA${NC}"
    echo -e "Database URL: ${YELLOW}postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME${NC}"
    echo ""
    echo -e "To start PostgreSQL manually:"
    echo -e "  ${YELLOW}$PG_BIN/pg_ctl -D $PG_DATA start${NC}"
    echo ""
    echo -e "To stop PostgreSQL:"
    echo -e "  ${YELLOW}$PG_BIN/pg_ctl -D $PG_DATA stop${NC}"
    echo ""
}

main "$@"
