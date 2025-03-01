#!/bin/bash

# TUNIX Security Configuration Script
# Copyright © Tarushv Kosgi 2025

set -e

LOG_FILE="/var/log/tunix/security-config.log"
SECURITY_CONFIG="/etc/tunix/security/config.json"
UFW_RULES="/etc/tunix/security/ufw-rules.conf"
AUDITD_RULES="/etc/audit/rules.d/tunix.rules"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

configure_firewall() {
    log_message "Configuring firewall..."
    
    # Reset UFW to default
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Load TUNIX rules
    while IFS= read -r rule; do
        [[ $rule =~ ^#.*$ ]] || [ -z "$rule" ] && continue
        ufw $rule
    done < "$UFW_RULES"
    
    # Enable firewall
    ufw --force enable
}

configure_selinux() {
    log_message "Configuring SELinux..."
    
    if command -v setenforce >/dev/null; then
        # Set SELinux to enforcing
        setenforce 1
        
        # Configure SELinux policies
        setsebool -P httpd_can_network_connect 1
        setsebool -P domain_can_mmap_files 1
    fi
}

configure_apparmor() {
    log_message "Configuring AppArmor..."
    
    # Enable AppArmor
    systemctl enable apparmor
    systemctl start apparmor
    
    # Load TUNIX profiles
    find /etc/apparmor.d/tunix -type f -name "*.profile" -exec apparmor_parser -r {} \;
}

configure_audit() {
    log_message "Configuring system auditing..."
    
    # Configure auditd
    cat > "$AUDITD_RULES" << EOF
# TUNIX Audit Rules

# Delete all existing rules
-D

# Set buffer size
-b 8192

# Monitor system calls
-a always,exit -F arch=b64 -S execve -k exec_calls
-a always,exit -F arch=b64 -S open -F exit=-EACCES -k access_denied
-a always,exit -F arch=b64 -S open -F exit=-EPERM -k access_denied

# Monitor sensitive files
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k sudo_actions
-w /etc/tunix/security -p wa -k tunix_security

# Monitor user activities
-w /var/log/auth.log -p wa -k auth_log
-w /var/log/syslog -p wa -k syslog
-w /var/log/tunix -p wa -k tunix_logs

# Monitor binary and library directories
-w /usr/bin -p wa -k binaries
-w /usr/sbin -p wa -k binaries
-w /usr/local/bin -p wa -k binaries
-w /usr/local/sbin -k binaries

# Make the configuration immutable
-e 2
EOF

    # Restart auditd
    service auditd restart
}

configure_pam() {
    log_message "Configuring PAM..."
    
    # Configure password quality
    cat > /etc/security/pwquality.conf << EOF
minlen = 12
minclass = 3
maxrepeat = 3
maxsequence = 3
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
dictcheck = 1
enforcing = 1
EOF

    # Configure login limits
    cat > /etc/security/limits.d/tunix.conf << EOF
* hard core 0
* soft nproc 10000
* hard nproc 10000
* soft nofile 64000
* hard nofile 64000
root soft nofile 64000
root hard nofile 64000
EOF
}

configure_kernel() {
    log_message "Configuring kernel security..."
    
    # Create sysctl configuration
    cat > /etc/sysctl.d/99-tunix-security.conf << EOF
# Network security
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_all = 1

# Kernel hardening
kernel.randomize_va_space = 2
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
kernel.core_uses_pid = 1
kernel.sysrq = 0
EOF

    # Apply sysctl settings
    sysctl --system
}

configure_ssh() {
    log_message "Configuring SSH..."
    
    # Backup existing config
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
    
    # Configure SSH
    cat > /etc/ssh/sshd_config << EOF
# TUNIX SSH Configuration
Protocol 2
PermitRootLogin no
MaxAuthTries 3
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitUserEnvironment no
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 30
EOF

    # Restart SSH service
    systemctl restart sshd
}

configure_crypto() {
    log_message "Configuring cryptographic policies..."
    
    # Set system-wide crypto policy
    if command -v update-crypto-policies >/dev/null; then
        update-crypto-policies set DEFAULT
    fi
    
    # Configure SSL/TLS settings
    cat > /etc/ssl/openssl.cnf << EOF
[system_default_sect]
MinProtocol = TLSv1.2
CipherString = HIGH:!aNULL:!MD5:!RC4
EOF
}

create_security_report() {
    log_message "Creating security report..."
    
    REPORT_FILE="/var/log/tunix/security-report.txt"
    
    {
        echo "TUNIX Security Configuration Report"
        echo "Generated: $(date)"
        echo "----------------------------------------"
        
        echo "Firewall Status:"
        ufw status
        
        echo -e "\nSELinux Status:"
        sestatus 2>/dev/null || echo "SELinux not installed"
        
        echo -e "\nAppArmor Status:"
        aa-status 2>/dev/null || echo "AppArmor not installed"
        
        echo -e "\nAudit Status:"
        auditctl -l
        
        echo -e "\nCrypto Policy:"
        update-crypto-policies --show 2>/dev/null || echo "Crypto policies not available"
        
    } > "$REPORT_FILE"
}

main() {
    log_message "Starting TUNIX security configuration"
    
    configure_firewall
    configure_selinux
    configure_apparmor
    configure_audit
    configure_pam
    configure_kernel
    configure_ssh
    configure_crypto
    create_security_report
    
    log_message "Security configuration completed successfully"
}

main