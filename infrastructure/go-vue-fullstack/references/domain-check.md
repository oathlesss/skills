# Domain Name Availability Check

Quick availability check without `whois`. Uses DNS nameservers as signal — if a domain has NS records, it's registered.

## Using `dig` (reliable)

```bash
dig +short NS domain.com
```

- **Has output** → domain is registered (taken)
- **Empty output** → domain is likely available

Batch check:

```bash
check_domain() {
  if dig +short NS "$1" 2>/dev/null | grep -q .; then
    echo "*** TAKEN:   $1"
  else
    echo "*** AVAIL:   $1"
  fi
}

for domain in fmt.dev neat.dev localfmt.dev; do
  check_domain "$domain"
done
```

Note: some registered domains may have no NS records configured (uncommon). False negatives are possible but rare. A domain with NS records is definitely taken.

## Using `host`

```bash
host -t NS domain.com
```

Returns `NXDOMAIN` or `SERVFAIL` if available, nameservers if taken.

## `.dev` TLD considerations

- `.dev` domains require HTTPS (HSTS preload on the TLD)
- Good for developer tools — communicates technical audience
- Typically $12-15/year at most registrars
- Both `host` and `dig` work normally with `.dev` TLD
