def passes_threshold(likes: int, member_count: int) -> bool:
    return likes * 10 >= member_count * 7


def category_weights(history):
    weights = {}
    for completed_round in history:
        for card in completed_round["cards"]:
            category = card["categoryId"]
            weights[category] = weights.get(category, 0) + card["likes"] - card["passes"]
    return weights


def order_candidates(items, weights):
    return sorted(items, key=lambda card: -weights.get(card["categoryId"], 0))
