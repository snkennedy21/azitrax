# Cloudflare Tunnel

Production ingress uses a remotely managed Cloudflare Tunnel. The
`cloudflared` container in `compose.prod.yaml` opens an outbound connection to
Cloudflare, so the host running Docker does not need inbound router port
forwarding.

## Cloudflare setup

Create a tunnel in the Cloudflare dashboard:

1. Go to **Zero Trust** or **Networking** > **Tunnels**.
2. Create a Cloudflare Tunnel for this app.
3. Choose the Docker connector setup and copy only the tunnel token value.
4. Add a public hostname route for the app.
5. Set the route service URL to:

```text
http://nginx:80
```

Cloudflare terminates public TLS. The tunnel forwards plain HTTP to the private
nginx service on the Docker network.

## Deployment environment

Store the tunnel token outside committed source files. Production deploys render
it through Ansible into `/srv/azitrax/.env` as:

```sh
CLOUDFLARED_TUNNEL_TOKEN=<token copied from Cloudflare>
```

`compose.prod.yaml` passes that value into the container as `TUNNEL_TOKEN`,
which is the environment variable supported by `cloudflared tunnel run` for
remotely managed tunnels.

Do not commit the tunnel token, Cloudflare API tokens, or any generated
Cloudflare credential files.
