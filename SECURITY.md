# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability** (private vulnerability reporting). Do not open a public issue or pull request for a vulnerability.

Include the affected version or commit, the steps to reproduce and the impact you observed.

## Supported versions

Only the default branch (`main`) is supported. Fixes land there.

## Scope

The app binds `127.0.0.1` only, reads local sources read-only and makes no outbound network call. Reports about the request guards, the CSP, file-system access during import or the public API are in scope.
