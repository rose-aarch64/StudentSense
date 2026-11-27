from ipaddress import ip_address

# Names that only resolve on a private network: mDNS, and a Tailscale tailnet.
_LOCAL_SUFFIXES = (".local", ".ts.net")


def is_near_host(host: str | None) -> bool:
    """Whether a host is on this machine or network, not on the internet."""
    if not host:
        return False
    try:
        # Loopback, private, link-local and Tailscale's 100.64.0.0/10 are all non-global.
        return not ip_address(host).is_global
    except ValueError:
        return host == "localhost" or host.endswith(_LOCAL_SUFFIXES)
