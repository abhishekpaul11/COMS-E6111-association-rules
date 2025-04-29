import sys
from itertools import combinations
from collections import defaultdict


def load_transactions(filename):
    transactions = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                items = [item.strip() for item in line.strip().split(',')]
                borough, time_period, fine_level, vehicle_type, violation_code, violation_desc = items

                violation_item = f"Violation_{violation_code}_{violation_desc}"

                new_items = [borough, time_period, fine_level, vehicle_type, violation_item]

                hierarchical_item = f"{fine_level}_{violation_item}"
                new_items.append(hierarchical_item)

                transactions.append(set(new_items))
        return transactions
    except FileNotFoundError:
        print(f"File {filename} not found")
        sys.exit(1)


def get_itemsets(transactions, k):
    """Generate candidate k-itemsets from transactions (initial pass for k=1)."""
    itemsets = set()
    for transaction in transactions:
        for combo in combinations(sorted(transaction), k):
            itemsets.add(frozenset(combo))
    return itemsets


def count_support(transactions, itemsets):
    """Count the support for each itemset in the transactions."""
    support_counts = defaultdict(int)
    for transaction in transactions:
        for itemset in itemsets:
            if itemset.issubset(transaction):
                support_counts[itemset] += 1
    return support_counts


def filter_frequent_itemsets(support_counts, min_sup, total_transactions):
    """Filter itemsets that meet the minimum support threshold."""
    min_support_count = min_sup * total_transactions
    frequent_itemsets = {itemset: count for itemset, count in support_counts.items() if count >= min_support_count}
    return frequent_itemsets


def generate_candidates(frequent_itemsets, k):
    """Generate candidate k-itemsets from frequent (k-1)-itemsets (Apriori-gen from Section 2.1.1)."""
    candidates = set()
    freq_list = [set(itemset) for itemset in frequent_itemsets.keys()]

    for i in range(len(freq_list)):
        for j in range(i + 1, len(freq_list)):
            itemset1 = freq_list[i]
            itemset2 = freq_list[j]
            union = itemset1.union(itemset2)
            if len(union) == k:
                candidates.add(frozenset(union))

    final_candidates = set()
    for candidate in candidates:
        all_subsets_frequent = True
        for subset in combinations(candidate, k - 1):
            if frozenset(subset) not in frequent_itemsets:
                all_subsets_frequent = False
                break
        if all_subsets_frequent:
            final_candidates.add(candidate)

    return final_candidates


def find_maximal_frequent_itemsets(frequent_itemsets):
    """Identify maximal frequent itemsets (not subsets of any other frequent itemset)."""
    maximal = set()
    sorted_itemsets = sorted(frequent_itemsets.keys(), key=len, reverse=True)

    for itemset in sorted_itemsets:
        is_maximal = True
        for other in maximal:
            if itemset.issubset(other):
                is_maximal = False
                break
        if is_maximal:
            maximal.add(itemset)

    return maximal


def apriori(transactions, min_sup):
    """Run the Apriori algorithm with variations."""
    total_transactions = len(transactions)

    # Step 1: Generate frequent 1-itemsets
    k = 1
    candidate_itemsets = get_itemsets(transactions, k)
    support_counts = count_support(transactions, candidate_itemsets)
    frequent_itemsets = filter_frequent_itemsets(support_counts, min_sup, total_transactions)

    all_frequent_itemsets = frequent_itemsets.copy()
    all_support_counts = support_counts.copy()

    # Step 2: Iteratively generate frequent k-itemsets
    k += 1
    while frequent_itemsets:
        candidates = generate_candidates(frequent_itemsets, k)
        if not candidates:
            break

        support_counts = count_support(transactions, candidates)
        frequent_itemsets = filter_frequent_itemsets(support_counts, min_sup, total_transactions)

        all_frequent_itemsets.update(frequent_itemsets)
        all_support_counts.update(support_counts)

        k += 1

    # Step 3: Find maximal frequent itemsets for rule generation
    maximal_frequent = find_maximal_frequent_itemsets(all_frequent_itemsets)

    return all_frequent_itemsets, all_support_counts, maximal_frequent, total_transactions


def generate_rules(maximal_frequent, support_counts, min_conf, total_transactions):
    """Generate association rules from maximal frequent itemsets with exactly one item on the RHS."""
    rules = []
    fine_levels = {"Low Fine", "Medium Fine", "High Fine"}

    for itemset in maximal_frequent:
        support = support_counts[itemset]
        if len(itemset) < 2:  # Skip 1-itemsets
            continue

        # Consider each item in the itemset as the RHS
        for rhs_item in itemset:
            # Skip hierarchical items as RHS
            if "_" in rhs_item and "Violation_" in rhs_item:
                continue
            rhs = frozenset([rhs_item])  # Exactly one item on the RHS
            lhs = frozenset(itemset - rhs)
            if not lhs:  # Ensure LHS has at least one item
                continue

            # Check for trivial rules: if RHS is a fine level, skip if LHS contains a hierarchical item with that fine level
            if rhs_item in fine_levels:
                is_trivial = False
                for lhs_item in lhs:
                    if lhs_item.startswith(f"{rhs_item}_Violation_"):
                        is_trivial = True
                        break
                if is_trivial:
                    continue

            # Compute confidence
            lhs_support = support_counts.get(lhs, 0)
            if lhs_support == 0:
                continue
            confidence = support / lhs_support
            if confidence >= min_conf:
                rule_support = support / total_transactions
                rules.append((lhs, rhs, rule_support, confidence))

    return rules


def save_results(frequent_itemsets, rules, total_transactions, min_sup, min_conf):
    """Save frequent itemsets and high-confidence rules to output.txt."""
    with open("output.txt", "w") as f:
        # Part 1: Frequent itemsets
        f.write(f"==Frequent itemsets (min_sup={min_sup * 100}%)\n")
        sorted_itemsets = sorted(frequent_itemsets.items(), key=lambda x: (-x[1], sorted(x[0])))
        for itemset, support in sorted_itemsets:
            support_percent = (support / total_transactions) * 100
            items = ",".join(sorted(itemset))
            f.write(f"[{items}], {support_percent:.1f}%\n")

        # Part 2: High-confidence rules
        f.write(f"\n==High-confidence association rules (min_conf={min_conf * 100}%)\n")
        sorted_rules = sorted(rules, key=lambda x: (-x[3], -x[2]))
        for lhs, rhs, support, confidence in sorted_rules:
            support_percent = support * 100
            confidence_percent = confidence * 100
            lhs_items = ",".join(sorted(lhs))
            rhs_items = ",".join(sorted(rhs))
            f.write(f"[{lhs_items}] => [{rhs_items}] (Conf: {confidence_percent:.1f}%, Supp: {support_percent:.1f}%)\n")


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 main.py <filename> <min_sup> <min_conf>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        min_sup = float(sys.argv[2])
        min_conf = float(sys.argv[3])
        if not (0 <= min_sup <= 1 and 0 <= min_conf <= 1):
            raise ValueError
    except ValueError:
        print("min_sup and min_conf must be numbers between 0 and 1")
        sys.exit(1)

    transactions = load_transactions(filename)
    frequent_itemsets, support_counts, maximal_frequent, total_transactions = apriori(transactions, min_sup)
    rules = generate_rules(maximal_frequent, support_counts, min_conf, total_transactions)
    save_results(frequent_itemsets, rules, total_transactions, min_sup, min_conf)

    print(f"Results written to output.txt")


if __name__ == "__main__":
    main()