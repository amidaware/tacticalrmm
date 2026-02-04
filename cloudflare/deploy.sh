#!/bin/bash
# Y12.AI Cloudflare Containers Deployment Script

set -e

echo "=========================================="
echo "  Y12.AI Cloudflare Containers Deployment"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    if ! command -v wrangler &> /dev/null; then
        echo -e "${RED}Error: wrangler CLI not found${NC}"
        echo "Install with: npm install -g wrangler"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: docker not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}Prerequisites OK${NC}"
}

# Build Docker images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"

    cd "$(dirname "$0")/.."

    # Backend
    echo "Building y12-backend..."
    docker build -t y12ai/y12-backend:latest -f docker/containers/tactical/dockerfile .

    # Frontend
    echo "Building y12-frontend..."
    docker build -t y12ai/y12-frontend:latest -f docker/containers/tactical-frontend/dockerfile .

    # NATS
    echo "Building y12-nats..."
    docker build -t y12ai/y12-nats:latest -f docker/containers/tactical-nats/dockerfile .

    echo -e "${GREEN}Images built successfully${NC}"
}

# Push to Cloudflare Registry
push_images() {
    echo -e "${YELLOW}Pushing images to Cloudflare Registry...${NC}"

    wrangler containers registry login

    for image in y12-backend y12-frontend y12-nats; do
        echo "Pushing $image..."
        docker tag y12ai/$image:latest registry.cloudflare.com/y12ai/$image:latest
        docker push registry.cloudflare.com/y12ai/$image:latest
    done

    echo -e "${GREEN}Images pushed successfully${NC}"
}

# Deploy to Cloudflare
deploy() {
    echo -e "${YELLOW}Deploying to Cloudflare Containers...${NC}"

    cd "$(dirname "$0")"
    wrangler containers deploy

    echo -e "${GREEN}Deployment complete${NC}"
}

# Run migrations
migrate() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    wrangler containers exec y12-backend -- python manage.py migrate

    echo -e "${GREEN}Migrations complete${NC}"
}

# Setup secrets (interactive)
setup_secrets() {
    echo -e "${YELLOW}Setting up secrets...${NC}"
    echo "You will be prompted to enter each secret value."

    echo -e "\n${YELLOW}Enter DATABASE_URL (PostgreSQL connection string):${NC}"
    wrangler secret put DATABASE_URL

    echo -e "\n${YELLOW}Enter REDIS_URL (Redis connection string):${NC}"
    wrangler secret put REDIS_URL

    echo -e "\n${YELLOW}Enter SECRET_KEY (Django secret, min 50 chars):${NC}"
    wrangler secret put SECRET_KEY

    echo -e "${GREEN}Secrets configured${NC}"
}

# Show help
show_help() {
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  all         Run full deployment (build, push, deploy, migrate)"
    echo "  build       Build Docker images"
    echo "  push        Push images to Cloudflare Registry"
    echo "  deploy      Deploy to Cloudflare Containers"
    echo "  migrate     Run database migrations"
    echo "  secrets     Configure secrets (interactive)"
    echo "  logs        View container logs"
    echo "  status      Show deployment status"
    echo "  help        Show this help message"
}

# View logs
view_logs() {
    echo -e "${YELLOW}Container logs:${NC}"
    wrangler containers logs y12-backend --tail=50
}

# Show status
show_status() {
    echo -e "${YELLOW}Deployment status:${NC}"
    wrangler containers list
}

# Main
case "${1:-help}" in
    all)
        check_prerequisites
        build_images
        push_images
        deploy
        migrate
        echo -e "${GREEN}=========================================="
        echo "  Deployment Complete!"
        echo "  Visit: https://y12.ai"
        echo "==========================================${NC}"
        ;;
    build)
        check_prerequisites
        build_images
        ;;
    push)
        check_prerequisites
        push_images
        ;;
    deploy)
        deploy
        ;;
    migrate)
        migrate
        ;;
    secrets)
        setup_secrets
        ;;
    logs)
        view_logs
        ;;
    status)
        show_status
        ;;
    help|*)
        show_help
        ;;
esac
