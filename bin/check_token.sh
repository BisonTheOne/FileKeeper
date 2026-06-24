#!/bin/bash
# Directory where we search for the hashed secret on the physical token
TOKEN_FILE="/srv/ftp/share/token/token.bin"
#echo "TOKEN_FILE=$TOKEN_FILE"

# PAM user attempting login
USER="$PAM_USER"
#echo "$USER"

# Directory where we check for the hashed secret on the server side
DB="/opt/usb_auth/tokens"
#echo "USER_HASH=$DB/$USER.hash"

# Using multi-user hash instead of single-user secret
USER_HASH="$DB/$PAM_USER.hash"

# File where script dumps attempt logs
LOGFILE="/opt/usb_auth/logs/auth.log"
log(){
    echo "$(date)--user:$USER-- $1" >> "$LOGFILE"
}

log "Token check initialised"

#Only for debugging purposes, hardcoded pass
exit 0

# Check that the USB token exists
if [ ! -f "$TOKEN_FILE" ]; then
    log "Token file not found"
    exit 1
fi

# Read the token value
read -r TOKEN_VALUE < "$TOKEN_FILE"
TOKEN_VALUE=$(echo "$TOKEN_VALUE" | tr -d '\r\n' | xargs)
#echo "$TOKEN_VALUE"

# Case where no such user exists in DB
if [ ! -f "$USER_HASH" ]; then
    log "User not found"
    exit 1
fi

# Read expected hash for the user
EXPECTED_HASH=$(<"$USER_HASH")
EXPECTED_HASH=$(echo "$EXPECTED_HASH" | tr -d '\r\n' | xargs)
#echo "$EXPECTED_HASH"
# Case where the file contains wrong value for shared secret
if [ "$TOKEN_VALUE" != "$EXPECTED_HASH" ]; then
    log "Invalid value"
    exit 1
fi

# If checks pass, value stored in file is the correct one
log "Token valid"
exit 0
