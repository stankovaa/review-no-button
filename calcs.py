"""
calcs.py — Founder proceeds calculation logic mirroring the Excel model.

Functions exported for cap_table.py:
    generate_exit_values         – 10-point exit x-axis
    compute_sell_today_proceeds  – Sell Today proceeds (current cap table, with liq pref)
    compute_founder_proceeds     – Raise & Sell proceeds (post-dilution, with liq pref)
    apply_risk                   – risk-adjust proceeds
    compute_desired_proceeds     – single target-exit desired amount

Key derived quantities (Excel cell equivalents):
    AL23  = (historical_pct + new_pct) x last_post_money   <- Sell Today liq pref threshold
    AM23  = raise_goal + historical_pct x last_post_money   <- Raise & Sell liq pref threshold
    AE28  = historical_pct + new_pct                        <- Sell Today investor ownership %
    AF28  = (raise_goal + historical_pct x pre_money) / post_money  <- Raise & Sell investor %
    AF19  = founders_pct x pre_money / post_money           <- diluted founder ownership
    AE42  = AF42 = founders_pct / (founders_pct + other_pct)  <- founder share of non-pref pool
      where other_pct = 1 - founders_pct - historical_pct - new_pct

Liquidation-preference waterfall (same structure for Sell Today and Raise & Sell):

    Non-Participating:
        Zone 1  V < liq_pref                -> 0
        Zone 2  liq_pref <= V < conversion  -> (V - liq_pref) x founder_nonpref_share
        Zone 3  V >= conversion             -> V x owner_pct
                (conversion = liq_pref / investor_pct)

    Participating (with cap multiple = pref_multiple):
        Zone 1  V < liq_pref                -> 0
        Zone 2  liq_pref <= V < cap_exit    -> (V - liq_pref) x owner_pct
        Zone 3  cap_exit <= V < conversion  -> proceeds_at_cap + (V - cap_exit) x founder_nonpref_share
        Zone 4  V >= conversion             -> V x owner_pct
                (cap_exit   = liq_pref + (pref_multiple-1) x liq_pref / investor_pct)
                (conversion = pref_multiple x liq_pref / investor_pct)
"""

import numpy as np

# Exit multiples matching Excel BM27:BM36 (0.25x to 4x of post-money valuation)
EXIT_COEFFICIENTS = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])


def generate_exit_values(min_exit: float) -> np.ndarray:
    """Return 10 exit valuations at [0.25x, 0.5x, ..., 4x] of min_exit.

    min_exit should be the post-money valuation (pre_money + raise_goal when
    show_new is True, else pre_money).  Mirrors Excel column BN formula:
        BN = IF(F15="Yes", AJ23 x BM, F18 x BM)
    """
    return EXIT_COEFFICIENTS * min_exit


def _liq_pref_waterfall(
    exit_vals,
    owner_pct,
    investor_pct,
    liq_pref_amount,
    pref_type,
    pref_multiple,
    founder_nonpref_share,
):
    """Apply a liquidation-preference waterfall and return founder proceeds.

    Used internally by both compute_sell_today_proceeds and compute_founder_proceeds.
    The caller supplies the scenario-specific owner_pct, investor_pct, and
    liq_pref_amount so the same zone logic handles both Sell Today and Raise & Sell.
    """
    is_participating = pref_type.strip().lower().startswith("part")

    if not is_participating:
        # Non-Participating: investors recover liq_pref_amount, then convert to equity.
        conversion = liq_pref_amount / investor_pct
        return np.where(
            exit_vals < liq_pref_amount,
            0.0,
            np.where(
                exit_vals < conversion,
                (exit_vals - liq_pref_amount) * founder_nonpref_share,
                exit_vals * owner_pct,
            ),
        )

    else:
        # Participating with cap multiple.
        # Cap exit: exit value where investor total return hits pref_multiple x liq_pref.
        cap_exit = liq_pref_amount + (pref_multiple - 1) * liq_pref_amount / investor_pct
        # Founder proceeds exactly at cap_exit (end of Zone 2, continuous at Zone 2/3 boundary):
        proceeds_at_cap = (cap_exit - liq_pref_amount) * owner_pct
        # Conversion: exit where investor equity value equals the cap amount.
        conversion = pref_multiple * liq_pref_amount / investor_pct
        return np.where(
            exit_vals < liq_pref_amount,
            0.0,
            np.where(
                exit_vals < cap_exit,
                (exit_vals - liq_pref_amount) * owner_pct,
                np.where(
                    exit_vals < conversion,
                    proceeds_at_cap + (exit_vals - cap_exit) * founder_nonpref_share,
                    exit_vals * owner_pct,
                ),
            ),
        )


def compute_sell_today_proceeds(
    exit_vals,
    founders_pct,
    historical_pct,
    new_pct,
    last_post_money,
    liq_pref,
    pref_type,
    pref_multiple,
):
    """Return Sell Today founder proceeds for each exit valuation.

    'Sell Today' evaluates the current cap table (no new round, no dilution).
    Mirrors Excel columns BP-BS (Non-Participating) and Participating Sell Today.

    Liq pref threshold (AL23) = (historical_pct + new_pct) x last_post_money.
    Investor ownership (AE28) = historical_pct + new_pct.
    Founder ownership used here is founders_pct (undiluted, AE19 = F28).
    """
    if not liq_pref:
        return exit_vals * founders_pct

    # AL23 - total investor capital at last round
    liq_pref_amount = (historical_pct + new_pct) * last_post_money
    investor_pct = historical_pct + new_pct

    # Edge case: no investors -> no preference
    if investor_pct <= 0 or liq_pref_amount <= 0:
        return exit_vals * founders_pct

    # AE42 = founders_pct / (founders_pct + other_pct)
    other_pct = max(0.0, 1.0 - founders_pct - historical_pct - new_pct)
    nonpref_total = founders_pct + other_pct
    founder_nonpref_share = founders_pct / nonpref_total if nonpref_total > 0 else 1.0

    return _liq_pref_waterfall(
        exit_vals,
        owner_pct=founders_pct,
        investor_pct=investor_pct,
        liq_pref_amount=liq_pref_amount,
        pref_type=pref_type,
        pref_multiple=pref_multiple,
        founder_nonpref_share=founder_nonpref_share,
    )


def compute_founder_proceeds(
    exit_vals,
    founders_pct,
    historical_pct,
    new_pct,
    pre_money,
    raise_goal,
    show_new,
    liq_pref,
    pref_type,
    pref_multiple,
    last_post_money=0.0,
):
    """Return Raise & Sell founder proceeds for each exit valuation.

    When show_new is False (no new round) the result equals Sell Today:
    founders_pct x exit_val, no dilution, no new-round liq pref.

    Liq pref threshold (AM23) = raise_goal + historical_pct x last_post_money.
    Investor ownership (AF28) = (raise_goal + historical_pct x pre_money) / post_money.
    Diluted founder ownership (AF19) = founders_pct x pre_money / post_money.
    """
    if not show_new or raise_goal <= 0:
        return exit_vals * founders_pct

    post_money = pre_money + raise_goal

    # AF19 - diluted founder ownership post-raise
    founders_dil = founders_pct * pre_money / post_money

    if not liq_pref:
        return exit_vals * founders_dil

    # AM23 - total investor capital (historical pro-rata + new external investors)
    liq_pref_amount = raise_goal + historical_pct * last_post_money

    # AF28 - total investor ownership post-raise
    investor_pct = (raise_goal + historical_pct * pre_money) / post_money

    if investor_pct <= 0 or liq_pref_amount <= 0:
        return exit_vals * founders_dil

    # AE42 = AF42 = founders_pct / (founders_pct + other_pct)
    other_pct = max(0.0, 1.0 - founders_pct - historical_pct - new_pct)
    nonpref_total = founders_pct + other_pct
    founder_nonpref_share = founders_pct / nonpref_total if nonpref_total > 0 else 1.0

    return _liq_pref_waterfall(
        exit_vals,
        owner_pct=founders_dil,
        investor_pct=investor_pct,
        liq_pref_amount=liq_pref_amount,
        pref_type=pref_type,
        pref_multiple=pref_multiple,
        founder_nonpref_share=founder_nonpref_share,
    )


def apply_risk(proceeds, risk_pct):
    """Return risk-adjusted proceeds: proceeds / (1 + risk_pct).

    Mirrors Excel AH{row} = AG{row} / (1 + F22) where F22 = 0.20.
    This is a present-value discount (dividing by the growth factor),
    not a simple percentage haircut.
    """
    return proceeds / (1.0 + risk_pct)


# def compute_desired_proceeds(
#     founders_pct,
#     pre_money,
#     raise_goal,
#     show_new,
#     exit_base,
# ):
#     """Return the founder's desired proceeds at the target exit valuation.

#     Mirrors Excel BM66 = F36 x AF19:
#         desired = exit_base x diluted_founders_pct
#     When show_new is False the undiluted founders_pct is used.
#     """
#     if show_new and raise_goal > 0:
#         post_money = pre_money + raise_goal
#         founders_dil = founders_pct * pre_money / post_money
#     else:
#         founders_dil = founders_pct
#     return founders_dil * exit_base

def compute_desired_proceeds(exit_vals, sell_today_vals, pre_money):
    """Return desired proceeds by interpolating the Sell Today curve at pre_money.

    Mirrors Excel AE11 = linear interpolation of (BO8:BO20, BP8:BP20) at AE10=pre_money.
    BO = exit valuations (exit_vals), BP = Sell Today proceeds (sell_today_vals).

    A (0, 0) anchor is prepended so that when pre_money falls below exit_vals[0]
    (which happens when pre_money < 0.25 x post_money) we interpolate from the
    origin rather than clamping to sell_today_vals[0].  At exit = 0, all proceeds
    are 0, so this anchor is always correct regardless of preference type.
    """
    xp = np.concatenate([[0.0], exit_vals])
    fp = np.concatenate([[0.0], sell_today_vals])
    return float(np.interp(pre_money, xp, fp))


def compute_callout_values(
    exit_vals,
    raise_sell_vals,
    founders_pct,
    pre_money,
    raise_goal,
    show_new,
    desired=None,
):
    """Return the five scalar values needed for the three callout boxes.

    Mirrors Excel cells (sheet 'Productisation Cap Table'):
        AF19  = founders_pct x pre_money / post_money       diluted ownership post-raise
        AG12  = 1 - AF19 / founders_pct                     dilution fraction
        AI10  = pre_money                                    Sell Today breakeven exit
                (= AI11/AI9 = founders_pct*pre_money / founders_pct)
        AG10  = linear interp on (raise_sell_vals, exit_vals) at target=founders_pct*pre_money
                i.e. the R&S exit value where proceeds equal current equity value
                (mirrors INDEX/MATCH with match_type=1 in BO/BQ tables)
        BM72  = AG10 / post_money                           breakeven exit multiple

    Returns a dict with keys:
        founders_dil_pct      float   AF19
        founders_dilution     float   AG12 (e.g. 0.143 = 14.3%)
        breakeven_sell_today  float   AI10 in raw dollars
        breakeven_raise_sell  float   AG10 in raw dollars
        breakeven_multiple    float   BM72
    """
    if not show_new or raise_goal <= 0:
        return {
            "founders_dil_pct": founders_pct,
            "founders_dilution": 0.0,
            "breakeven_sell_today": pre_money,
            "breakeven_raise_sell": pre_money,
            "breakeven_multiple": 1.0,
        }

    post_money = pre_money + raise_goal

    # AF19
    founders_dil_pct = founders_pct * pre_money / post_money if post_money > 0 else 0.0

    # AG12
    founders_dilution = 1.0 - founders_dil_pct / founders_pct if founders_pct > 0 else 0.0

    # AI10: Sell Today breakeven exit = pre_money
    # Proof: Sell Today proceeds = founders_pct * exit → exit = (founders_pct * pre_money) / founders_pct
    breakeven_sell_today = pre_money

    # AG10: R&S breakeven exit — mirrors Excel AF53 formula exactly
    # AF46 = desired proceeds (passed in, or fall back to founders_pct * pre_money)
    target = desired if desired is not None else founders_pct * pre_money

    # Excel: IF(AF46<=0, 0, IF(AF46<=BQ8, ..., IF(AF46>BQ20, extrapolate, interp)))
    if target <= 0:
        breakeven_raise_sell = 0.0
    elif target <= raise_sell_vals[0]:
        # Below first point: proportional scaling from origin
        if raise_sell_vals[0] == 0:
            breakeven_raise_sell = 0.0
        else:
            breakeven_raise_sell = float(target / raise_sell_vals[0] * exit_vals[0])
    elif target > raise_sell_vals[-1]:
        # Above last point: linear extrapolation using last two points
        # Excel: IF(BQ20=BQ19, BO20, BO19+(AF46-BQ19)/(BQ20-BQ19)*(BO20-BO19))
        bq19, bq20 = float(raise_sell_vals[-2]), float(raise_sell_vals[-1])
        bo19, bo20 = float(exit_vals[-2]), float(exit_vals[-1])
        if bq20 == bq19:
            breakeven_raise_sell = bo20
        else:
            breakeven_raise_sell = bo19 + (target - bq19) / (bq20 - bq19) * (bo20 - bo19)
    else:
        breakeven_raise_sell = float(np.interp(target, raise_sell_vals, exit_vals))

    # BM72 = AG10 / post_money (breakeven exit multiple)
    breakeven_multiple = breakeven_raise_sell / post_money if post_money > 0 else 0.0

    return {
        "founders_dil_pct": founders_dil_pct,
        "founders_dilution": founders_dilution,
        "breakeven_sell_today": breakeven_sell_today,
        "breakeven_raise_sell": breakeven_raise_sell,
        "breakeven_multiple": breakeven_multiple,
    }
    