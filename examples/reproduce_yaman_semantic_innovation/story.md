# Reproduce: Semantic knowledge guides innovation in cumulative cultural evolution

## Source

This is a faithful reproduction of the agent-based model in Yaman, Tian &
Lindström, "Semantic knowledge guides innovation and drives cultural
evolution" (PNAS 2026). Every mechanism below is from the paper; the goal
is to rebuild the ABM and reproduce its qualitative findings, not to
invent a mechanism.

## The phenomenon

A population of agents performs a **combinatorial innovation task**.
Agents that hold *semantic knowledge* — a learned sense of which items
function together — innovate more, and the advantage compounds
synergistically with social learning. The headline result: semantic
knowledge directs exploration toward meaningful item combinations, raises
innovation success, and accelerates cumulative cultural evolution, even
when using that knowledge carries a cost.

## Agents

Each agent (the population is 100 individuals) holds:

- an **inventory** of items (everyone starts with the 6 base items),
- a **memory** of recipes (item combinations) it has already tried,
- an **age** (integer, increments each generation),
- a **score** (number of innovations discovered), and
- a **semantic model**: a small feedforward neural network with one
  hidden layer of 16 units, ReLU activation, and a softmax output over
  all items. Given one item as input, it predicts a probability
  distribution over the item that would complete a successful recipe.
  Each item also has a learned **embedding** vector (size 16). The
  network and embeddings are trained by cross-entropy loss and
  backpropagation on every successful recipe the agent has acquired.

## The innovation task (the "Totem" recipe tree)

- There are 6 initial items.
- New items are produced by valid recipes that combine **at most 3**
  existing items.
- The recipe tree has 11 levels; the number of reachable items per level
  is 6, 4, 2, 2, 2, 3, 3, 7, 11, 48, 96.
- A recipe is "valid" if it matches a defined combination; a valid recipe
  the agent has not seen yields a new item added to its inventory.
- **The specific recipes are NOT a formula — they are released data.** The
  full innovation tree is provided in the paper's data file
  `rules_tidied.csv` (from the OSF repository): one row per item, with
  ingredient columns `c1,c2,c3` (item ids, `0` = empty slot), the produced
  `item`, a `given` flag for the 6 base items, a `point` score, and a
  `name_simplified` label. The model LOADS this table; it does not enumerate
  or invent the combinations.

## What an agent does on one innovation attempt (Algorithm 2)

Each attempt picks a strategy by two probabilities, `P_S` (use the
semantic model) and `P_G` (generalize):

1. **Random** (probability 1 − P_S): pick 1–3 items from inventory
   uniformly at random and try that combination.
2. **Semantic** (probability P_S, then 1 − P_G): pick a first item at
   random, then use the semantic model to predict the complementary
   second (and, for 3-item recipes, third) item. Try that combination.
3. **Generalization** (probability P_S × P_G): take one remembered
   successful recipe and replace one of its items with the item that is
   nearest in embedding space.

If the resulting combination is new to memory and is a valid recipe, the
agent gains the new item. Either way the attempt is added to memory.

## The population loop (Algorithm 1, cumulative cultural evolution)

Each generation:

1. Each agent makes a fixed number of innovation attempts. With
   probability `P_SL` (social learning) the agent instead inspects the
   highest-scoring agent's inventory and, if it can craft a missing item
   from its own inventory, copies that recipe; otherwise it falls back to
   an individual attempt.
2. All agents **retrain their semantic models** on every successful
   recipe acquired so far (own and socially learned).
3. Agents die with an age-based probability (older agents more likely);
   the dead are replaced by **offspring of higher-scoring parents**.
   Offspring inherit the parent's *semantic model* but start with only
   the 6 base items — so cultural knowledge (the model) transmits, but
   specific artifacts (items) must be re-earned.

This Moran-style turnover lets the cultural repertoire and the semantic
knowledge co-evolve over generations.

## Parameters

- Population size N = 100 (the paper also tests 25 and 50).
- Semantic model: 1 hidden layer, 16 units; item embedding size 16.
- Strategy probabilities P_S, P_SL, P_G each take values in
  {0, 0.1, 0.5, 0.9} in the paper's sweep.
- Semantic-model use can carry a cost (baseline 1×, robust up to 3×).
- Death probability is age-based (increasing with age).

## What I want to observe

- Innovation success (cumulative items discovered) over generations,
  compared between populations WITH semantic knowledge (P_S > 0) and
  WITHOUT (P_S = 0).
- The interaction between semantic knowledge and social learning:
  whether P_S > 0 and P_SL > 0 together amplify innovation more than
  either alone.
- Whether the semantic advantage persists across population sizes.

The target metric per generation is the population's mean cumulative
innovation count (size of the cultural repertoire).
