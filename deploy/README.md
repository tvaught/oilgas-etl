# `openhollow` Deployment

Deploy the authenticated reporting app at `https://oilgas.openhollow.com`.

## Google OAuth

1. In Google Cloud Console, create or select a project.
2. Configure the OAuth consent screen as **External** (or Internal if every user belongs to one Workspace).
3. Add each approved person as a test user until the consent screen is published.
4. Create a Web application OAuth client with this authorized redirect URI:

   ```text
   https://oilgas.openhollow.com/auth/google/callback
   ```

5. Record the client ID and client secret. Never commit either value.

## Server configuration

Create `/etc/oilgas.env` on `openhollow` from `oilgas.env.example`:

```bash
sudo vim /etc/oilgas.env
sudo chown root:oilgas /etc/oilgas.env
sudo chmod 640 /etc/oilgas.env
```

Generate a session secret on the server:

```bash
openssl rand -hex 32
```

Set `OILGAS_ALLOWED_EMAILS` to the comma-separated, lower-case email addresses permitted to access the app.

## Service and reverse proxy

Install the committed service and Nginx files:

```bash
sudo cp deploy/oilgas.service /etc/systemd/system/oilgas.service
sudo cp deploy/oilgas.openhollow.com.nginx /etc/nginx/sites-available/oilgas.openhollow.com
sudo ln -s /etc/nginx/sites-available/oilgas.openhollow.com /etc/nginx/sites-enabled/oilgas.openhollow.com
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now oilgas
sudo systemctl reload nginx
```

Obtain HTTPS only after the HTTP proxy responds successfully:

```bash
sudo certbot --nginx -d oilgas.openhollow.com --redirect
```

## Application data

The service expects these host paths:

```text
/srv/oilgas/data/oilgas.duckdb
/srv/oilgas/data/raw/
```

Sync the DuckDB database and matching raw source PDFs before starting the service. The app serves PDFs from the absolute source paths persisted at ingestion time, so ingest on `openhollow` using `/srv/oilgas/data/raw/`, or update the stored paths during the data migration.

## Updating application code

As `travis`:

Use the committed deployment helper from the application checkout:

```bash
cd /srv/oilgas/app
./deploy/update.sh
```

The script fast-forwards the checkout, installs the lockfile-pinned dependencies,
repairs group read/execute permissions, restarts `oilgas`, and prints service status
and the last 100 service-log lines. It must be run as the deployment user (`travis`),
which has passwordless or interactive `sudo` access for the required commands.
