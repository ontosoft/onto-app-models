# Caddy with the RFC 2136 DNS provider compiled in.
#
# The stock image ships no DNS provider modules, and without one only the
# inbound challenge types (http-01, tls-alpn-01) are available. Neither works
# here: the public CAs are blocked by the campus firewall, and the internal
# CA's validators cannot reach the VM on 80/443 either (verified empirically
# over both IPv4 and IPv6 — campus-internal hosts reach the ports fine).
#
# dns-01 inverts the direction. Caddy writes a TXT record under
# _acme-challenge.<host> over RFC 2136, authenticated with the zone's TSIG
# key, and the CA reads it from DNS. Nothing has to reach us inbound.
#
# Versions are pinned rather than floating. caddy:2-* is any 2.x, and the
# plugin without a version resolves to whatever is newest at build time, so
# two builds weeks apart produce different images without a line changing
# here. That matters because the deploy rebuilds on the VM: a rebuild whose
# output differs moves the tag to a new image while the running container
# still points at the old one — which then gets collected, and compose can no
# longer resolve the container's image.
FROM caddy:2.11.4-builder AS builder

RUN xcaddy build v2.11.4 --with github.com/caddy-dns/rfc2136@v1.0.0

FROM caddy:2.11.4-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
