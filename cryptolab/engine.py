"""Search bounded token graphs, simulate reserve-mutating multihop routes and greedily allocate split trades."""

from .validation import integer, identifier
import copy


def pool_quote(pool, token, amount):
    fee = integer(pool.get("fee_bps", 30), maximum=9999)
    a = pool["token_a"]
    b = pool["token_b"]
    if token == a:
        ri, ro = pool["reserve_a"], pool["reserve_b"]
        output_token = b
        reverse = False
    elif token == b:
        ri, ro = pool["reserve_b"], pool["reserve_a"]
        output_token = a
        reverse = True
    else:
        raise ValueError("token not in pool")
    effective = amount * (10000 - fee)
    out = effective * ro // (ri * 10000 + effective)
    if out <= 0:
        raise ValueError("dust route")
    if reverse:
        pool["reserve_b"] += amount
        pool["reserve_a"] -= out
    else:
        pool["reserve_a"] += amount
        pool["reserve_b"] -= out
    return output_token, out


def routes(pools, source, target, hops):
    found = []

    def visit(token, path, seen):
        if token == target:
            if path:
                found.append(path)
            return
        if len(path) >= hops:
            return
        for key, pool in sorted(pools.items()):
            if key in path or token not in (pool["token_a"], pool["token_b"]):
                continue
            next_token = (
                pool["token_b"] if token == pool["token_a"] else pool["token_a"]
            )
            if next_token not in seen:
                visit(next_token, path + [key], seen | {next_token})
            if len(found) > 500:
                raise ValueError("route search exceeds 500 paths")

    visit(source, [], {source})
    return found


def execute_route(pools, path, source, amount):
    state = copy.deepcopy(pools)
    token = source
    output = amount
    legs = []
    for key in path:
        before = state[key]["reserve_a"] * state[key]["reserve_b"]
        token, output = pool_quote(state[key], token, output)
        if state[key]["reserve_a"] * state[key]["reserve_b"] < before:
            raise ValueError("reserve invariant failed")
        legs.append({"pool": key, "output_token": token, "output_amount": output})
    return output, state, legs


def analyze(data):
    pools = {}
    for item in data["pools"]:
        key = identifier(item["id"])
        if key in pools or item["token_a"] == item["token_b"]:
            raise ValueError("invalid pool")
        pools[key] = {
            **item,
            "reserve_a": integer(item["reserve_a"], minimum=1),
            "reserve_b": integer(item["reserve_b"], minimum=1),
        }
        integer(item.get("fee_bps", 30), maximum=9999)
    if len(pools) > 30:
        raise ValueError("at most 30 pools")
    source = identifier(data["source"])
    target = identifier(data["target"])
    if source == target:
        raise ValueError("source and target must differ")
    amount = integer(data["amount"], minimum=1)
    hops = integer(data.get("max_hops", 3), minimum=1, maximum=5)
    chunks = integer(data.get("chunks", 10), minimum=1, maximum=100)
    paths = routes(pools, source, target, hops)
    if not paths:
        raise ValueError("no route")
    single = []
    for path in paths:
        try:
            out, _, legs = execute_route(pools, path, source, amount)
            single.append({"path": path, "output": out, "legs": legs})
        except ValueError:
            continue
    if not single:
        raise ValueError("all routes produce dust")
    single.sort(key=lambda r: (-r["output"], r["path"]))
    state = copy.deepcopy(pools)
    allocations = []
    total = 0
    chunks = min(chunks, amount)
    base, remainder = divmod(amount, chunks)
    for index in range(chunks):
        piece = base + (index < remainder)
        candidates = []
        for path in paths:
            try:
                out, next_state, legs = execute_route(state, path, source, piece)
                candidates.append((out, path, next_state, legs))
            except ValueError:
                continue
        if not candidates:
            raise ValueError("split chunk produces dust; reduce chunks")
        candidates.sort(key=lambda r: (-r[0], r[1]))
        out, path, state, legs = candidates[0]
        total += out
        allocations.append({"input": piece, "output": out, "path": path, "legs": legs})
    return {
        "best_single": single[0],
        "single_routes": single,
        "split_output": total,
        "split_allocations": allocations,
        "final_pools": state,
        "algorithm": "bounded path enumeration plus greedy sequential chunks",
        "route_count": len(paths),
    }
