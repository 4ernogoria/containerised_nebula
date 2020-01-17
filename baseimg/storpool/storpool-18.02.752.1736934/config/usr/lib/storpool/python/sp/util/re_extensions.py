"""Provides regular expressions function utilities."""

def matches(matcher, strings):
    """Try to match each string with matcher and return list of all matches."""
    return [m for m in map(matcher.match, strings) if m is not None]


def all_matches(matchers, strings):
    """Try to match each string with each matcher and return list of all matches."""
    return [matches(matcher, strings) for matcher in matchers]
