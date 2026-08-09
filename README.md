# FileKeeper

A small Flask web UI that authenticates users using an HMAC challenge/response (per-user secret files) and provides file management (list/upload/download/delete) against an FTP backend.

## Key features

- Challenge/response authentication using per-user secret files at `/etc/webauthn/users/<username>.secret`.
- FTP backend (ftplib) for storing and retrieving user files.
- Minimal web UI (HTML/CSS) in `web/templates` and static assets in `web/static`.

## Requirements

- Python 3.8+
- Flask
- An FTP server reachable at the configured host and port
- File system access to create per-user secret files and the log directory

## Quickstart (local, minimal)

> These steps assume you have an FTP server running and reachable at 127.0.0.1:21 and that you're running as a user with permission to create the required system paths.

```bash
# create per-user secret dir and example user
sudo mkdir -p /etc/webauthn/users
echo "mysecret" | sudo tee /etc/webauthn/users/alice.secret > /dev/null
sudo chmod 600 /etc/webauthn/users/alice.secret

# create log dir
sudo mkdir -p /opt/usb_auth/logs
sudo chown $(whoami) /opt/usb_auth/logs

# run the app locally
python -m venv venv
source venv/bin/activate
pip install flask
python web/app.py
# open http://localhost:8080
```

## Configuration

The app's configuration is currently hardcoded in `web/app.py`:

- `FTP_HOST` and `FTP_PORT` (defaults: `127.0.0.1`, `21`)
- `LOG_FILE` (defaults: `/opt/usb_auth/logs/auth.log`)
- `app.secret_key` (defaults: `usb_auth_project_key`)

For a production-ready deployment you should:

- Move these to environment variables and don't commit secrets.
- Replace the hardcoded `app.secret_key` with a secure random value stored outside the repository.
- Avoid storing plaintext FTP passwords in the Flask session (current code stores `session["pass"]`). Consider using server-side sessions or another credential flow.
- Use FTPS/SFTP instead of plain FTP where possible.

## Security notes

- Per-user secrets are read from the host filesystem (`/etc/webauthn/users/<username>.secret`) — ensure proper filesystem permissions (600) and ownership.
- The current session stores the FTP password in the Flask session (which by default is a signed cookie). This is insecure for production; consider changing to server-side session storage.
- The `app.secret_key` in the repository is not secure — replace with a strong secret.

## Project layout

```
.gitignore
bin/                    # helper scripts (e.g. check_token.sh)
docs/                   # docs
web/                    # Flask app and web assets
  app.py                # main Flask application (routes, auth, FTP integration)
  templates/            # HTML templates (login, dashboard, about)
  static/               # CSS, favicon
```

## Next steps 

- Adding a `requirements.txt` or `pyproject.toml` with pinned dependencies.
- Adding a Dockerfile and/or systemd unit for deployment.
- Replacing filesystem-based secrets with a safer secret store or at least document secret creation steps more fully.
- Adding tests around the authentication flow and FTP interactions (mock FTP server).

## Contributing

Feel free to open issues or PRs. If you change authentication or storage, include migration/deployment notes.

