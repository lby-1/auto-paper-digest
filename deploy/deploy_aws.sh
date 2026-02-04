#!/bin/bash
# AWS EC2 Deployment Script for Auto-Paper-Digest
# Usage: ./deploy_aws.sh [instance-type] [key-pair-name]

set -e

INSTANCE_TYPE=${1:-t3.medium}
KEY_PAIR=${2:-apd-key}
SECURITY_GROUP=${3:-apd-sg}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "==================================================="
echo "Auto-Paper-Digest AWS Deployment"
echo "==================================================="
echo "Instance Type: $INSTANCE_TYPE"
echo "Key Pair: $KEY_PAIR"
echo "Security Group: $SECURITY_GROUP"
echo "Region: $REGION"
echo "==================================================="

# Step 1: Create Security Group if not exists
echo "Creating security group..."
aws ec2 create-security-group \
    --group-name $SECURITY_GROUP \
    --description "Security group for Auto-Paper-Digest" \
    --region $REGION \
    2>/dev/null || echo "Security group already exists"

# Allow SSH
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region $REGION \
    2>/dev/null || echo "SSH rule already exists"

# Allow HTTP for portal
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp \
    --port 7860 \
    --cidr 0.0.0.0/0 \
    --region $REGION \
    2>/dev/null || echo "HTTP rule already exists"

# Step 2: Create user data script
cat > /tmp/apd-user-data.sh << 'EOF'
#!/bin/bash
# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /home/ec2-user
git clone https://github.com/brianxiadong/auto-paper-digest.git
cd auto-paper-digest

# Create .env file (will need to be configured later)
cat > .env << 'ENVEOF'
HF_TOKEN=YOUR_HF_TOKEN_HERE
HF_USERNAME=YOUR_USERNAME_HERE
HF_DATASET_NAME=paper-digest-videos
MIN_QUALITY_SCORE=60.0
ENVEOF

chown -R ec2-user:ec2-user /home/ec2-user/auto-paper-digest

# Start services
docker-compose up -d

echo "Auto-Paper-Digest deployed successfully!"
echo "Please SSH into the instance and configure .env file with your credentials"
EOF

# Step 3: Launch EC2 instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_PAIR \
    --security-groups $SECURITY_GROUP \
    --user-data file:///tmp/apd-user-data.sh \
    --region $REGION \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=auto-paper-digest}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance ID: $INSTANCE_ID"

# Step 4: Wait for instance to be running
echo "Waiting for instance to be running..."
aws ec2 wait instance-running \
    --instance-ids $INSTANCE_ID \
    --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "==================================================="
echo "Deployment completed!"
echo "==================================================="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "SSH Command: ssh -i $KEY_PAIR.pem ec2-user@$PUBLIC_IP"
echo "Portal URL: http://$PUBLIC_IP:7860"
echo ""
echo "Next steps:"
echo "1. SSH into the instance"
echo "2. Edit /home/ec2-user/auto-paper-digest/.env with your credentials"
echo "3. Restart services: cd auto-paper-digest && docker-compose restart"
echo "==================================================="

# Clean up
rm /tmp/apd-user-data.sh
