#!/bin/bash

# GDriveProtect Kubernetes Deployment Script
# This script deploys the GDriveProtect application to Kubernetes
# Optimized for Google Workspace Marketplace compliance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
NAMESPACE="gdriveprotect"
MARKETPLACE_MODE=${MARKETPLACE_MODE:-"false"}

if [ "$ENVIRONMENT" = "development" ]; then
    NAMESPACE="gdriveprotect-dev"
    IMAGE_TAG="dev"
fi

echo -e "${BLUE}🚀 Deploying GDriveProtect to Kubernetes${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Namespace: ${NAMESPACE}${NC}"
echo -e "${BLUE}Image Tag: ${IMAGE_TAG}${NC}"
echo -e "${BLUE}Marketplace Mode: ${MARKETPLACE_MODE}${NC}"
echo ""

# Function to check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed. Please install kubectl first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ kubectl found${NC}"
}

# Function to check if cluster is accessible
check_cluster() {
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Connected to Kubernetes cluster${NC}"
}

# Function to run security scans
run_security_scans() {
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "${YELLOW}🔒 Running security scans for marketplace compliance...${NC}"
        
        # Check if trivy is available
        if command -v trivy &> /dev/null; then
            echo -e "${YELLOW}📋 Scanning filesystem for vulnerabilities...${NC}"
            trivy fs --severity HIGH,CRITICAL . || {
                echo -e "${RED}❌ Critical vulnerabilities found. Please fix before deployment.${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}📋 Scanning Docker image for vulnerabilities...${NC}"
            trivy image --severity HIGH,CRITICAL gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG} || {
                echo -e "${RED}❌ Critical vulnerabilities found in image. Please fix before deployment.${NC}"
                exit 1
            }
        else
            echo -e "${YELLOW}⚠️  Trivy not found. Skipping security scans.${NC}"
            echo -e "${YELLOW}   Install trivy: https://aquasecurity.github.io/trivy/latest/getting-started/installation/${NC}"
        fi
        
        echo -e "${GREEN}✅ Security scans completed${NC}"
    fi
}

# Function to build and push Docker image
build_image() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    
    # Build the image
    docker build -t gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG} .
    
    echo -e "${YELLOW}📤 Pushing Docker image...${NC}"
    
    # Push to Google Container Registry
    docker push gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG}
    
    echo -e "${GREEN}✅ Image built and pushed successfully${NC}"
}

# Function to update image tag in deployment
update_image() {
    echo -e "${YELLOW}�� Updating image tag in deployment...${NC}"
    
    # Update the image tag in the deployment file
    if [ "$ENVIRONMENT" = "development" ]; then
        sed -i.bak "s|gcr.io/your-project/gdriveprotect:dev|gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG}|g" k8s/deployment.yaml
    else
        sed -i.bak "s|gcr.io/your-project/gdriveprotect:latest|gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG}|g" k8s/deployment.yaml
    fi
    
    echo -e "${GREEN}✅ Image tag updated${NC}"
}

# Function to deploy to Kubernetes
deploy_k8s() {
    echo -e "${YELLOW}📦 Deploying to Kubernetes...${NC}"
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply core Kubernetes manifests
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/serviceaccount.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    kubectl apply -f k8s/hpa.yaml
    
    # Apply marketplace-specific configurations if enabled
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "${YELLOW}🏪 Applying marketplace configurations...${NC}"
        kubectl apply -f k8s/marketplace-config.yaml
        kubectl apply -f k8s/network-policy.yaml
        kubectl apply -f k8s/pod-disruption-budget.yaml
        echo -e "${GREEN}✅ Marketplace configurations applied${NC}"
    fi
    
    echo -e "${GREEN}✅ Kubernetes manifests applied${NC}"
}

# Function to wait for deployment
wait_for_deployment() {
    echo -e "${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        kubectl rollout status deployment/gdriveprotect-dev -n ${NAMESPACE} --timeout=300s
    else
        kubectl rollout status deployment/gdriveprotect -n ${NAMESPACE} --timeout=300s
    fi
    
    echo -e "${GREEN}✅ Deployment is ready${NC}"
}

# Function to check application health
check_health() {
    echo -e "${YELLOW}🏥 Checking application health...${NC}"
    
    # Wait a bit for the application to start
    sleep 10
    
    # Check if pods are running
    if [ "$ENVIRONMENT" = "development" ]; then
        kubectl get pods -n ${NAMESPACE} -l app=gdriveprotect,environment=development
    else
        kubectl get pods -n ${NAMESPACE} -l app=gdriveprotect
    fi
    
    # Check service
    kubectl get svc -n ${NAMESPACE}
    
    # Check marketplace-specific resources if enabled
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "${YELLOW}🏪 Checking marketplace resources...${NC}"
        kubectl get networkpolicy -n ${NAMESPACE}
        kubectl get pdb -n ${NAMESPACE}
        kubectl get configmap -n ${NAMESPACE} -l marketplace=true
    fi
    
    echo -e "${GREEN}✅ Health check completed${NC}"
}

# Function to validate marketplace compliance
validate_marketplace_compliance() {
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "${YELLOW}🏪 Validating marketplace compliance...${NC}"
        
        # Check required labels
        echo -e "${YELLOW}📋 Checking required labels...${NC}"
        kubectl get deployment -n ${NAMESPACE} -o jsonpath='{.items[*].metadata.labels}' | grep -q "marketplace=true" || {
            echo -e "${RED}❌ Missing marketplace labels${NC}"
            return 1
        }
        
        # Check security policies
        echo -e "${YELLOW}🔒 Checking security policies...${NC}"
        kubectl get networkpolicy -n ${NAMESPACE} | grep -q "gdriveprotect" || {
            echo -e "${RED}❌ Network policies not found${NC}"
            return 1
        }
        
        # Check resource limits
        echo -e "${YELLOW}📊 Checking resource limits...${NC}"
        kubectl get deployment -n ${NAMESPACE} -o jsonpath='{.items[*].spec.template.spec.containers[*].resources.limits}' | grep -q "memory" || {
            echo -e "${RED}❌ Resource limits not configured${NC}"
            return 1
        }
        
        echo -e "${GREEN}✅ Marketplace compliance validation passed${NC}"
    fi
}

# Function to show deployment info
show_info() {
    echo -e "${BLUE}📊 Deployment Information:${NC}"
    echo -e "${BLUE}Namespace: ${NAMESPACE}${NC}"
    echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
    echo -e "${BLUE}Image: gcr.io/${PROJECT_ID}/gdriveprotect:${IMAGE_TAG}${NC}"
    echo -e "${BLUE}Marketplace Mode: ${MARKETPLACE_MODE}${NC}"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${BLUE}Production URL: https://gdriveprotect.yourdomain.com${NC}"
    else
        echo -e "${BLUE}Development URL: https://dev-gdriveprotect.yourdomain.com${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}🔍 Useful commands:${NC}"
    echo -e "  kubectl get pods -n ${NAMESPACE}"
    echo -e "  kubectl logs -f deployment/gdriveprotect -n ${NAMESPACE}"
    echo -e "  kubectl describe deployment gdriveprotect -n ${NAMESPACE}"
    echo -e "  kubectl get svc -n ${NAMESPACE}"
    echo -e "  kubectl get ingress -n ${NAMESPACE}"
    
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "  kubectl get networkpolicy -n ${NAMESPACE}"
        echo -e "  kubectl get pdb -n ${NAMESPACE}"
        echo -e "  kubectl get configmap -n ${NAMESPACE} -l marketplace=true"
    fi
}

# Function to cleanup
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
    
    # Restore original deployment file
    if [ -f k8s/deployment.yaml.bak ]; then
        mv k8s/deployment.yaml.bak k8s/deployment.yaml
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main deployment flow
main() {
    echo -e "${BLUE}🚀 Starting GDriveProtect Kubernetes deployment...${NC}"
    echo ""
    
    # Pre-deployment checks
    check_kubectl
    check_cluster
    
    # Security scans for marketplace
    run_security_scans
    
    # Build and deploy
    build_image
    update_image
    deploy_k8s
    wait_for_deployment
    check_health
    
    # Validate marketplace compliance
    validate_marketplace_compliance
    
    # Show deployment information
    show_info
    
    # Cleanup
    cleanup
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    
    if [ "$MARKETPLACE_MODE" = "true" ]; then
        echo -e "${GREEN}🏪 Application is ready for Google Workspace Marketplace submission!${NC}"
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build")
        check_kubectl
        check_cluster
        build_image
        ;;
    "deploy-k8s")
        check_kubectl
        check_cluster
        deploy_k8s
        wait_for_deployment
        check_health
        ;;
    "security-scan")
        run_security_scans
        ;;
    "validate-compliance")
        validate_marketplace_compliance
        ;;
    "health")
        check_health
        ;;
    "info")
        show_info
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {deploy|build|deploy-k8s|security-scan|validate-compliance|health|info|cleanup}"
        echo ""
        echo "Commands:"
        echo "  deploy              - Full deployment (build, push, deploy to k8s)"
        echo "  build               - Build and push Docker image only"
        echo "  deploy-k8s          - Deploy to Kubernetes only (assumes image exists)"
        echo "  security-scan       - Run security scans for marketplace compliance"
        echo "  validate-compliance - Validate marketplace compliance requirements"
        echo "  health              - Check application health"
        echo "  info                - Show deployment information"
        echo "  cleanup             - Clean up temporary files"
        echo ""
        echo "Environment variables:"
        echo "  PROJECT_ID      - Google Cloud Project ID (default: your-project-id)"
        echo "  IMAGE_TAG       - Docker image tag (default: latest)"
        echo "  ENVIRONMENT     - Environment to deploy (production|development, default: production)"
        echo "  MARKETPLACE_MODE - Enable marketplace compliance features (true|false, default: false)"
        exit 1
        ;;
esac
