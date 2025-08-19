#!/bin/bash

# TalkAI Deployment Script
set -e

echo "🚀 Starting TalkAI deployment..."

# Configuration
PROJECT_NAME="talkai"
BACKEND_DIR="./backend"
FRONTEND_DIR="./frontend"
SERVER_USER="ubuntu"
SERVER_HOST="your-server-ip"  # Replace with your server IP
DOMAIN="your-domain.com"      # Replace with your domain

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || error "Docker is not installed"
    command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is not installed"
    
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        warn ".env file not found in backend directory"
        echo "Please create .env file with required environment variables:"
        echo "  - MOONSHOT_API_KEY or OPENAI_API_KEY"
        echo "  - WECHAT_APP_ID and WECHAT_APP_SECRET"
        echo "  - SECRET_KEY"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Copy dictionary database
setup_dictionary() {
    log "Setting up dictionary database..."
    
    if [ -f "../dictionary400k.db" ]; then
        log "Copying dictionary database..."
        cp "../dictionary400k.db" "$BACKEND_DIR/data/db/"
    else
        warn "Dictionary database not found at ../dictionary400k.db"
        echo "Please ensure the dictionary database is available"
    fi
}

# Deploy backend
deploy_backend() {
    log "Deploying backend..."
    
    cd "$BACKEND_DIR"
    
    # Build and start containers
    docker-compose down || true
    docker-compose build --no-cache
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 10
    
    # Health check
    for i in {1..30}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log "Backend is healthy!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Backend health check failed"
        fi
        sleep 2
    done
    
    cd ..
}

# Deploy frontend (instructions)
deploy_frontend() {
    log "Frontend deployment instructions:"
    echo
    echo -e "${BLUE}To deploy the WeChat Mini Program frontend:${NC}"
    echo "1. Open WeChat Developer Tools"
    echo "2. Import the project from: $(pwd)/$FRONTEND_DIR"
    echo "3. Update the API base URL in frontend/services/api.js:"
    echo "   const BASE_URL = 'https://$DOMAIN/api/v1';"
    echo "4. Configure WeChat Mini Program settings:"
    echo "   - Add server domain: https://$DOMAIN"
    echo "   - Configure request domain whitelist"
    echo "5. Upload and submit for review"
    echo
}

# Setup SSL (Let's Encrypt)
setup_ssl() {
    log "SSL setup instructions:"
    echo
    echo -e "${BLUE}To enable HTTPS:${NC}"
    echo "1. Install Certbot:"
    echo "   sudo apt update && sudo apt install certbot"
    echo "2. Obtain SSL certificate:"
    echo "   sudo certbot certonly --standalone -d $DOMAIN"
    echo "3. Copy certificates:"
    echo "   sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem backend/ssl/cert.pem"
    echo "   sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem backend/ssl/key.pem"
    echo "4. Uncomment HTTPS configuration in nginx.conf"
    echo "5. Restart services: docker-compose restart"
    echo
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo
    cd "$BACKEND_DIR"
    docker-compose ps
    echo
    log "API Endpoints:"
    echo "  Health Check: http://localhost:8000/health"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Base API URL: http://localhost:8000/api/v1"
    echo
    cd ..
}

# Backup database
backup_database() {
    log "Creating database backup..."
    
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/talkai_backup_$TIMESTAMP.tar.gz"
    
    tar -czf "$BACKUP_FILE" -C "$BACKEND_DIR" data/
    log "Database backed up to: $BACKUP_FILE"
}

# Main deployment process
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════╗"
    echo "║           TalkAI Deployment          ║"
    echo "║     English Learning Mini Program    ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_prerequisites
    setup_dictionary
    deploy_backend
    deploy_frontend
    setup_ssl
    show_status
    
    log "✅ Deployment completed successfully!"
    echo
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Configure your domain DNS to point to this server"
    echo "2. Set up SSL certificate using the instructions above"
    echo "3. Deploy the WeChat Mini Program frontend"
    echo "4. Test the complete application workflow"
    echo
    echo -e "${YELLOW}Important:${NC}"
    echo "- Monitor logs: docker-compose logs -f"
    echo "- Restart services: docker-compose restart"
    echo "- Update: git pull && ./deploy.sh"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        backup_database
        ;;
    "status")
        show_status
        ;;
    "logs")
        cd "$BACKEND_DIR"
        docker-compose logs -f
        ;;
    "restart")
        cd "$BACKEND_DIR"
        docker-compose restart
        ;;
    "stop")
        cd "$BACKEND_DIR"
        docker-compose down
        ;;
    *)
        echo "Usage: $0 {deploy|backup|status|logs|restart|stop}"
        exit 1
        ;;
esac