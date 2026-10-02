# Contributing

Open an issue describing the input, expected output and actual behavior. Include a minimal synthetic fixture with no credentials.

For a patch, add a domain regression test, run `python3 -m unittest discover -s tests -v`, and regenerate the expected fixture if the documented behavior changes. Keep runtime dependencies minimal, use integer or Decimal arithmetic for values, and document rounding and trust assumptions.

Do not include wallet keys, copied proprietary source, fabricated usage statistics or misleading claims of an audit.
