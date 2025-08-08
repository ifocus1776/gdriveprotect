#!/bin/bash

# Google Drive Setup Script for GDriveProtect
# This script helps you set up OAuth 2.0 authentication for personal Google Drive access

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Google Drive Setup for GDriveProtect${NC}"
echo "=============================================="

# Function to check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ Google Cloud SDK is not installed${NC}"
        echo "Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    echo -e "${GREEN}✅ Google Cloud SDK found${NC}"
}

# Function to check if user is authenticated
check_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${YELLOW}⚠️  You are not authenticated with gcloud${NC}"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    echo -e "${GREEN}✅ User is authenticated${NC}"
}

# Function to create OAuth 2.0 credentials
create_oauth_credentials() {
    echo -e "${BLUE}🔐 Creating OAuth 2.0 credentials...${NC}"
    
    # Get current project
    PROJECT_ID=$(gcloud config get-value project)
    echo "Using project: $PROJECT_ID"
    
    # Create OAuth 2.0 client ID
    echo -e "${YELLOW}📋 Creating OAuth 2.0 client ID...${NC}"
    echo "1. Go to: https://console.cloud.google.com/apis/credentials"
    echo "2. Click 'Create Credentials' > 'OAuth 2.0 Client IDs'"
    echo "3. Choose 'Desktop application'"
    echo "4. Name it: 'GDriveProtect Desktop Client'"
    echo "5. Download the JSON file"
    echo ""
    
    read -p "Have you downloaded the OAuth credentials JSON file? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ OAuth credentials ready${NC}"
    else
        echo -e "${RED}❌ Please download the OAuth credentials first${NC}"
        exit 1
    fi
}

# Function to set up application default credentials
setup_adc() {
    echo -e "${BLUE}🔑 Setting up Application Default Credentials...${NC}"
    
    # Try to set up ADC
    if gcloud auth application-default login --no-launch-browser 2>/dev/null; then
        echo -e "${GREEN}✅ Application Default Credentials set up successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not set up ADC automatically${NC}"
        echo "You may need to set up credentials manually:"
        echo "1. Run: gcloud auth application-default login"
        echo "2. Follow the browser authentication flow"
    fi
}

# Function to enable required APIs
enable_apis() {
    echo -e "${BLUE}🔌 Enabling required Google APIs...${NC}"
    
    APIs=(
        "drive.googleapis.com"
        "dlp.googleapis.com"
        "storage.googleapis.com"
        "cloudkms.googleapis.com"
        "pubsub.googleapis.com"
    )
    
    for api in "${APIs[@]}"; do
        echo -n "Enabling $api... "
        if gcloud services enable "$api" --quiet; then
            echo -e "${GREEN}✅${NC}"
        else
            echo -e "${YELLOW}⚠️  (may already be enabled)${NC}"
        fi
    done
}

# Function to create service account (alternative method)
create_service_account() {
    echo -e "${BLUE}👤 Creating service account for domain-wide delegation...${NC}"
    
    PROJECT_ID=$(gcloud config get-value project)
    SA_NAME="gdriveprotect-sa"
    SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Create service account
    if gcloud iam service-accounts create "$SA_NAME" --display-name="GDriveProtect Service Account" 2>/dev/null; then
        echo -e "${GREEN}✅ Service account created${NC}"
    else
        echo -e "${YELLOW}⚠️  Service account may already exist${NC}"
    fi
    
    # Grant necessary permissions
    echo "Granting permissions..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/dlp.user"
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/storage.admin"
    
    # Create key file
    echo "Creating service account key..."
    gcloud iam service-accounts keys create "gdriveprotect-sa-key.json" \
        --iam-account="$SA_EMAIL"
    
    echo -e "${GREEN}✅ Service account key created: gdriveprotect-sa-key.json${NC}"
}

# Function to provide Docker run commands
show_docker_commands() {
    echo -e "${BLUE}🐳 Docker Run Commands${NC}"
    echo "=========================="
    
    echo ""
    echo "1. With OAuth 2.0 credentials (recommended for personal use):"
    echo "   Place your OAuth JSON file in the project directory as 'oauth_credentials.json'"
    echo "   docker run -p 5000:5000 \\"
    echo "     -e GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \\"
    echo "     -v \$(pwd)/oauth_credentials.json:/app/oauth_credentials.json:ro \\"
    echo "     -e GOOGLE_APPLICATION_CREDENTIALS=/app/oauth_credentials.json \\"
    echo "     gdriveprotect"
    
    echo ""
    echo "2. With service account (for domain-wide delegation):"
    echo "   docker run -p 5000:5000 \\"
    echo "     -e GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \\"
    echo "     -v \$(pwd)/gdriveprotect-sa-key.json:/app/service-account-key.json:ro \\"
    echo "     -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json \\"
    echo "     gdriveprotect"
    
    echo ""
    echo "3. With application default credentials:"
    echo "   docker run -p 5000:5000 \\"
    echo "     -e GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \\"
    echo "     -v ~/.config/gcloud:/app/.config/gcloud:ro \\"
    echo "     gdriveprotect"
}

# Function to test the setup
test_setup() {
    echo -e "${BLUE}🧪 Testing the setup...${NC}"
    
    # Check if container is running
    if docker ps | grep -q gdriveprotect; then
        echo -e "${GREEN}✅ Container is running${NC}"
        
        # Test endpoints
        echo "Testing endpoints..."
        if curl -s http://localhost:5000/api/dlp/health >/dev/null; then
            echo -e "${GREEN}✅ DLP health endpoint working${NC}"
        else
            echo -e "${RED}❌ DLP health endpoint failed${NC}"
        fi
        
        if curl -s http://localhost:5000/api/drive/health >/dev/null; then
            echo -e "${GREEN}✅ Drive health endpoint working${NC}"
        else
            echo -e "${RED}❌ Drive health endpoint failed${NC}"
        fi
        
        if curl -s http://localhost:5000/api/vault/health >/dev/null; then
            echo -e "${GREEN}✅ Vault health endpoint working${NC}"
        else
            echo -e "${RED}❌ Vault health endpoint failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Container is not running${NC}"
        echo "Please start the container first"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting Google Drive setup...${NC}"
    
    # Check prerequisites
    check_gcloud
    check_auth
    
    # Enable APIs
    enable_apis
    
    # Set up credentials
    echo ""
    echo -e "${BLUE}📋 Choose your authentication method:${NC}"
    echo "1. OAuth 2.0 (recommended for personal Google Drive)"
    echo "2. Service Account with Domain-Wide Delegation"
    echo "3. Application Default Credentials"
    
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            create_oauth_credentials
            show_docker_commands
            ;;
        2)
            create_service_account
            show_docker_commands
            ;;
        3)
            setup_adc
            show_docker_commands
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Choose one of the Docker run commands above"
    echo "2. Start the container with proper credentials"
    echo "3. Access the web interface at http://localhost:5000"
    echo "4. Test Google Drive access through the API endpoints"
    
    # Test if container is running
    test_setup
}

# Run main function
main "$@"
