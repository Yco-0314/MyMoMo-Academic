# ABM Model Design Document — Reproduction

**Status**: Draft
**Mode**: REPRODUCE

---

## Part 0: Source Paper Reference

- **Citation**: Scholl, Mahfouz, Calinescu & Farmer, "Learning to Manage Investment Portfolios beyond Simple Utility Functions", ICAIF'25
- **DOI / URL**: Not provided (accepted at ICAIF'25)
- **Key claim being reproduced**: Agent fund-manager strategies can be modelled as learned conditional distributions over portfolio weights, parameterized by an 8-dimensional latent strategy vector, using a conditional GAN architecture
- **Fidelity target**: The learned latent space captures recognizable fund investment styles (e.g., growth vs value); sampling latent strategies yields diverse, realistic synthetic portfolios conditioned on market state
- **Acceptable deviation**: Exact discriminator training dynamics may not perfectly replicate due to random weight initialization; qualitative latent-space structure (clustering by style) is the primary result, not exact numerical values

---

## Part 1: Requirements

### 1. Model Overview

- **Project Name**: FundManagerGAN
- **Original Story**: Reproduce the conditional GAN model from Scholl et al. (ICAIF'25) where each agent fund manager carries a learned strategy encoder and portfolio allocator, trained adversarially on 1436 US equity mutual funds' quarterly holdings
- **Goal**: Reproduce the finding that the learned 8-dimensional latent strategy space recovers known investment styles
- **Mode**: Trainer (adversarial GAN training)
- **Visualizer**: Yes — latent space visualization (e.g., t-SNE/PCA of phi), portfolio weight distributions, style clustering

### 2. Agents

- **Agent Class**: FundManager
  - **Attributes**:
    - `latent_strategy: np.ndarray` (8-dim) — learned strategy encoding [paper-canonical]: "phi_a is an 8-dimensional latent vector encoding manager a's strategy"
    - `current_weights: np.ndarray` (N=500 stocks) — current portfolio allocation [paper-canonical]: "w are portfolio weights over N=500 stocks"
    - `prev_weights: np.ndarray` (N=500 stocks) — previous period allocation [paper-canonical]: "conditioned on ... previous weights"
    - `return_history: np.ndarray` (T x N) — last T periods of returns [paper-canonical]: "r is a history of T periods of returns"
    - `characteristics_history: np.ndarray` (T x K) — asset characteristics [paper-canonical]: "X are K asset characteristics"
    - `fund_id: int` — unique identifier [template-owned]
  - **Methods**:
    - `encode_strategy()` — runs strategy encoder E_phi on observed allocation and returns [paper-canonical]
    - `generate_portfolio(market_state)` — runs portfolio allocator D_w conditioned on market state and latent phi [paper-canonical]
    - `step()` — calls generate_portfolio() with current market state [paper-canonical]
  - **Initialization**:
    - `latent_strategy` initialized from standard normal N(0,1) for each agent [paper-canonical]: strategy encoder is trained, not initialized from data
    - `current_weights` initialized to equal weights across N stocks (1/N) [AI-ASSUMPTION: story/lit silent on initial weights; standard ABM practice for portfolio models]
    - `prev_weights` initialized same as current_weights [AI-ASSUMPTION: no prior period exists at t=0]
    - `return_history` initialized to zeros [AI-ASSUMPTION: no history available before simulation start]
    - `characteristics_history` initialized to zeros [AI-ASSUMPTION: same reasoning]

### 3. Space & Environment

- **Space Structure**: No topology — agents interact through the market environment only, not with each other directly [derived from topology decision tree: agents respond to global market state, not to other agents]
- **Grid Specs / Network Specs**: Not applicable
- **Environment Logic**: 
  - `MarketModel` (VAE) generates synthetic stock universe: characteristics X and returns r for N=500 stocks [paper-canonical]
  - Carhart four-factor model embedded structurally: r = alpha + sum_k beta_k y_k + epsilon [paper-canonical]
  - Each simulation step: (1) market model generates new market state; (2) each agent reads market state and generates portfolio; (3) discriminator evaluates (portfolio, market_state) pairs

### 4. Optimization

- **Calibrator/Trainer**: Trainer (adversarial GAN)
- **Trainer Type**: Generative Adversarial Network with four components:
  1. Market model (VAE) — generator of synthetic stock universes [paper-canonical]
  2. Strategy encoder E_phi — maps (w, X, r) to 8-dim latent phi via three attention lanes [paper-canonical]
  3. Portfolio allocator D_w — generates portfolio weights from (phi, market_state, prev_weights) [paper-canonical]
  4. Discriminator — distinguishes real (portfolio, market) from generated; trained adversarially [paper-canonical]
- **Training Parameters**: Adversarial training (generator vs discriminator) [paper-canonical], specific hyperparameters (learning rates, batch sizes) from paper if available, else standard defaults

### 5. Data

- **Inputs**: 
  - `fund_holdings.csv` — 1436 US equity mutual funds' quarterly holdings [paper-canonical]
  - `carhart_factors.csv` — Carhart factor loadings precomputed from CRSP [paper-canonical]
- **Outputs**:
  - Learned 8-dim latent strategies phi per fund [paper-canonical]
  - Generated synthetic portfolios [paper-canonical]
  - Discriminator loss values [analysis]
  - t-SNE/PCA of latent space [analysis: visualization]

### 6. Computing

- **Parallel Cores**: 4 (sensible default for training on typical research hardware)
- **Parallel Mode**: process (GPU-based training benefits from multi-core data loading)

---

## Part 2: Technical Specification

### 1. File Structure

- `core/agent.py`: `FundManager`, `MarketAgent` (for synthetic agents)
- `core/model.py`: `GANModel` (orchestrates training)
- `core/environment.py`: `MarketEnvironment` (holds market state)
- `core/scenario.py`: `GANScenario`
- `core/data_collector.py`: `FundDataCollector`
- `core/components/`: 
  - `market_model.py` — VAE for market state generation
  - `strategy_encoder.py` — E_phi neural network
  - `portfolio_allocator.py` — D_w generator network
  - `discriminator.py` — discriminator network
- `main.py`: entry point for training

### 2. Class Interfaces

#### Agent
```python
class FundManager(Agent):
    def setup(self):
        self.latent_strategy = np.random.normal(0, 1, 8)  # 8-dim latent phi
        self.current_weights = np.ones(500) / 500  # equal weight initialization
        self.prev_weights = self.current_weights.copy()
        self.return_history = np.zeros((T, 500))  # T from scenario
        self.characteristics_history = np.zeros((T, K))  # K from scenario
    
    def step(self):
        # reads market state from environment
        market_state = self.environment.get_market_state()
        # generates new portfolio weights
        self.prev_weights = self.current_weights.copy()
        self.current_weights = self.generate_portfolio(market_state)
    
    def encode_strategy(self, weights, returns, characteristics):
        # runs E_phi attention-based encoder
        # returns 8-dim latent phi
        pass
    
    def generate_portfolio(self, market_state):
        # runs D_w decoder conditioned on phi, market_state, prev_weights
        # returns sparse valid allocation
        pass
```

#### Model
```python
class GANModel(Model):
    def create(self):
        self.agents = self.create_agent_list(FundManager)
        self.environment = self.create_environment(MarketEnvironment)
        self.data_collector = self.create_data_collector(FundDataCollector)
        # Neural components
        self.market_model = MarketVAE(
            n_stocks=self.scenario.n_stocks,
            n_factors=self.scenario.n_factors  # Carhart 4-factor
        )
        self.strategy_encoder = StrategyEncoder(
            latent_dim=8,
            n_stocks=self.scenario.n_stocks,
            n_characteristics=self.scenario.n_characteristics
        )
        self.portfolio_allocator = PortfolioAllocator(
            latent_dim=8,
            n_stocks=self.scenario.n_stocks
        )
        self.discriminator = Discriminator(
            n_stocks=self.scenario.n_stocks,
            n_characteristics=self.scenario.n_characteristics
        )
    
    def setup(self):
        # Initialize agents from training data
        self.agents.setup_agents(
            agents_num=self.scenario.agent_num,  # 1436 from paper
            from_csv="fund_holdings.csv"
        )
        # Precompute Carhart loadings
        self.environment.setup(
            carhart_factors_csv="carhart_factors.csv"
        )
    
    def run(self):
        for t in self.iterator(self.scenario.periods):
            # 1. Generate synthetic market state
            market_state = self.market_model.generate()
            self.environment.update_market_state(market_state)
            
            # 2. Agents generate portfolios
            for agent in self.agents:
                agent.step()
            
            # 3. Discriminator evaluates
            real_pairs = self._sample_real_data()
            generated_pairs = [(a.current_weights, market_state) for a in self.agents]
            disc_loss = self.discriminator.train_step(real_pairs, generated_pairs)
            
            # 4. Generator trained adversarially
            gen_loss = self._train_generator()
            
            self.data_collector.collect(t, disc_loss=disc_loss, gen_loss=gen_loss)
        self.data_collector.save()
```

### 3. Data Inputs Plan

- **SimulatorScenarios.csv columns**:
  - `n_stocks`: int — number of stocks in universe (500 from paper)
  - `n_characteristics`: int — K asset characteristics (specific value from paper if stated)
  - `n_factors`: int — number of Carhart factors (4 from paper)
  - `return_history_len`: int — T periods of return history
  - `agent_num`: int — number of fund managers (1436 from paper)
  - `latent_dim`: int — dimension of latent strategy space (8 from paper)
  - `training_epochs`: int — training iterations
  - `batch_size`: int — minibatch size for GAN training

- **Other input CSVs**:
  - `fund_holdings.csv`: fund_id, quarter, stock_id, weight, characteristics_cols...
  - `carhart_factors.csv`: date, market_return, smb, hml, umd

### 4. Output Data

- `Result_Simulator_Agent.csv`: fund_id, period, latent_strategy_0..7, top_10_weights, style_label
- `Result_Simulator_Environment.csv`: period, discriminator_loss, generator_loss, mean_portfolio_entropy, factor_exposure_0..3

### 5. Source Trace

| Element | Source | Detail |
|---|---|---|
| 1. Agents | paper-canonical | "Each agent is a fund manager... strategy encoded as 8-dim latent phi" |
| 2. Interaction | paper-canonical | No direct agent interaction; agents respond to market environment via market model (VAE) |
| 3. Time | paper-canonical | Discrete time steps (quarterly holdings data); T periods of history |
| 4. Initialization | AI-ASSUMPTION (2 tags) | Equal-weight initial portfolio; zero return history |
| 5. Decisions | paper-canonical | Portfolio allocator D_w conditioned on (phi, market_state, prev_weights) |
| 6. Scenarios | paper-canonical | N=500 stocks, Carhart 4-factor, 8-dim latent, 1436 funds |
| 7. Calibration | paper-canonical | Adversarial GAN training on 1436 funds' quarterly holdings with CRSP factors |
| 8. Output | paper-canonical | Latent strategies phi, generated portfolios, style clustering visualization |

### 6. Assumptions (AI-ASSUMPTION only — last resort)

1. **Initial portfolio weights** (Agent attribute initialization):
   - Source check: story silent | lit_notes silent | no canonical default known for FundManagerGAN
   - Reason: Standard ABM practice for portfolio models to start with equal weights; paper doesn't specify initial conditions for generated portfolios
   - Value: `current_weights = np.ones(500) / 500`

2. **Initial return/characteristics history** (Agent attribute initialization):
   - Source check: story silent | lit_notes silent | no canonical default known
   - Reason: No historical data before simulation start; zeros are neutral initialization
   - Value: `return_history = np.zeros((T, 500))`, `characteristics_history = np.zeros((T, K))`

3. **Market model generation schedule** (Environment logic):
   - Source check: story silent | lit_notes silent | no canonical default known
   - Reason: Paper doesn't specify how often market states are generated; monthly/quarterly alignment with training data is reasonable
   - Value: Market state generated once per training epoch, synchronized with data batches

4. **Discriminator architecture details** (Neural network structure):
   - Source check: story silent | lit_notes silent | no canonical default known
   - Reason: Paper describes high-level architecture (attention, three lanes) but not layer counts or activation functions; standard GAN architectures for financial data applied
   - Value: Standard MLP with 2 hidden layers (256, 128 units), ReLU activations, dropout 0.3, using Wasserstein GAN objective with gradient penalty

**Total AI-ASSUMPTION tags: 4** (within ≤5 limit, viable)