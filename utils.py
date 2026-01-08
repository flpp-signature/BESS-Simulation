# -*- coding: utf-8 -*-
"""
Utility functions for BESS simulation.

Contains helper functions for printing, rounding, and other common operations.
"""

import random


def custom_print(message: str, log_file: str = 'error_log.txt') -> None:
    """
    Print both to console and log file.
    
    Args:
        message: The message to print and log
        log_file: Path to the log file (default: 'error_log.txt')
    """
    print(message)
    with open(log_file, 'a') as of:
        of.write(message + '\n')


def true_round(number, precision: int = 3):
    """
    True rounding that handles floating point arithmetic issues.
    
    This is needed to handle some floating point arithmetic issues, 
    which break comparisons sometimes.
    
    Args:
        number: Number or array-like to round
        precision: Number of decimal places (default: 3)
    
    Returns:
        Rounded number or array
    """
    return round(number + 1e-15, precision)


def id_clearing(bid: float, id_liquidity: float) -> float:
    """
    Simulate ID (Intraday) market liquidity clearing.
    
    Args:
        bid: The bid amount
        id_liquidity: Probability of successful clearing (0-1)
    
    Returns:
        The bid amount if cleared successfully, 0 otherwise
    """
    return (random.random() <= id_liquidity) * bid
