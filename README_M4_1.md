# M4.1 KA9Q Status Receiver

Copy the package contents into the repository root, preserving paths.

This implementation deliberately separates multicast transport from the exact
KA9Q status wire decoder. The receiver is production-usable once a verified
`StatusDatagramDecoder` for the selected radiod release is supplied.

Run:

```bash
python3 -m pytest -q
```
