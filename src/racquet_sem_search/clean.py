import pandas as pd
import numpy as np
import re

def validate_raw_columns(df: pd.DataFrame):
    """Checks that raw dataset has all expected columns.

    Args:
        df (pd.DataFrame): The raw, scraped dataset

    Returns:
        bool: True if all expected columns exist, False if not.
    """
    required = {'racquet_url', 'racquet_img', 'racquet_name', 'racquet_rating', 
                'racquet_rating_count', 'racquet_price', 'racquet_description', 
                'head_size', 'length', 'strung_weight', 'balance', 'swingweight', 
                'stiffness', 'beam_width', 'composition', 'power_level', 'stroke_style', 
                'swing_speed',
       'racquet_colors', 'grip_type', 'string_pattern', 'string_tension',
       'age', 'weight', 'height', 'other', 'age_9-10', 'strung _weight'}
    
    missing = required - set(df.columns)
    
    if missing:
        raise ValueError(f"Raw data is missing required columns: {missing}")

def drop_name_and_url_nas(df: pd.DataFrame) -> pd.DataFrame:
    """Drops the NA values from racquet_url and racquet_name.

    Args:
        df (pd.DataFrame): The raw, scraped dataset

    Returns:
        pd.DataFrame: Raw dataset without NA names or URLs
    """
    out = df.copy()
    out = out.dropna(subset = ["racquet_name", "racquet_url"])
    
    return out

def add_brand_column(df: pd.DataFrame) -> pd.DataFrame:
    """Extract brand name from racquet_name and creates a new
    column for brand.

    Args:
        df (pd.DataFrame): The raw, scraped dataset WITHOUT
        URL or name NAs

    Returns:
        pd.DataFrame: Raw dataset with racquet brand column
    """
    out = df.copy()
    out["racquet_brand"] = out["racquet_name"].apply(lambda x: x.split(" ")[0])
    
    return out

def add_id_column(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts the racquet's SKU from its URL
    and uses it to create a unique ID column.

    Args:
        df (pd.DataFrame): The raw, scraped dataset WITHOUT
        URL or name NAs

    Returns:
        pd.DataFrame: Raw dataset with racquet_id column
    """
    out = df.copy()
    
    out["racquet_id"] = out["racquet_url"].apply(lambda x: x.split("/")[::-1][0].split(".")[0].replace("descpage", ""))

    return out

def remove_junior_racquets(df:pd.DataFrame) -> pd.DataFrame:
    """Remove any racquets with "Junior" in their names.

    Args:
        df (pd.DataFrame): The modified raw dataframe with the added 
        racquet_brand and racquet_id column

    Returns:
        pd.DataFrame: Dataframe with junior racquets removed
    """
    out = df[~df["racquet_name"].str.lower().str.strip().str.contains("junior")].copy()
    return out

def drop_majority_NA_cols(df:pd.DataFrame) -> pd.DataFrame:
    """Drop all columns with more than 95% NA values.

    Args:
        df (pd.DataFrame): Dataframe with junior racquets removed

    Returns:
        pd.DataFrame: Dataframe with racquet brand column, junior racquets removed, 
        and majority NA columns dropped
    """
    
    out = df.copy()
    
    # Get cols with >95% NA
    cols_to_drop = []
    for col in out.columns:
        if out[col].isna().sum() == 0:
            pass
        elif out[col].isna().sum() / out.shape[0] > 0.95:
            cols_to_drop.append(col)
        else:
            pass
        
    out = out.drop(columns = cols_to_drop) 
    return out

def extract_numeric_specs(df:pd.DataFrame) -> pd.DataFrame:
    """Use regex functions to convert string columns with non-standard formatting to float values.

    Args:
        df (pd.DataFrame): DataFrame with majority NA columns dropped

    Returns:
        pd.DataFrame: DataFrame with racquet brand column, junior racquets removed, 
        majority NA columns dropped, and string columns transformed
    """
    
    out = df.copy()
    
    ###############
    # HEAD SIZE
    ###############
    
    # Extract racquet head size in sq. inches
    out["racquet_head_size_sq_in"] = (
        out["head_size"]\
            .str.extract(r"(\d+\.?\d*)\s*(?:in²|in|sq\s*in)")\
                .astype(float)
                )
    
    ###############
    # LENGTH
    ###############
    
    # Extract racquet length in inches
    out["racquet_length_in"] = (
        out["length"]\
            .str.extract(r"(\d+\.?\d*)\s*(?:in²|in|sq\s*in)")\
                .astype(float)
                )
    
    ###############
    # STRUNG WEIGHT
    ###############
    
    # Extract strung weight in ounces 
    out["racquet_strung_weight_oz"] = (
        out["strung_weight"]\
            .str.extract(r"(\d+\.?\d*)\s*")\
                .astype(float)
                )
    
    ###############
    # BALANCE
    ###############
    
    # Extract racquet balance inches value
    out["racquet_balance_in"] = (
        out["balance"]\
            .str.extract(r"(\d+(?:\.\d+)?)\s*in\b")\
                .astype(float)
                )
    
    # Extract Balance number and label separately
    extracted = out["balance"].str.extract(
        r"(\d+(?:\.\d+)?)\s*(?:pts\s*)?(HL|HH|EB)\b"
    )

    extracted.columns = ["value", "label"]

    extracted["value"] = extracted["value"].astype(float)

    # Balance helper function
    def apply_balance_sign(row):
        if row["label"] == "HL":
            return row['value']
        elif row["label"] == "HH":
            return -row["value"]
        elif row["label"] == "EB":
            return 0.0
        return None

    # Extract and apply discrete head light indicator
    out["racquet_balance_HH_HL"] = extracted.apply(apply_balance_sign, axis = 1)
    
    ###############
    # STIFFNESS
    ###############
    
    # Extract racquet stiffness
    out["racquet_stiffness"] = out["stiffness"]
    out['racquet_stiffness'] = out['racquet_stiffness'].replace('N/A (very low)', np.nan)
    out["racquet_stiffness"] = out["racquet_stiffness"].astype(float)
    
    ###############
    # AVG BEAM WIDTH
    ###############
    
    # Calculate avg. beam width helper
    def average_beam_width(value):
        if isinstance(value, str):
            parts = value.split("/")
            numbers = []
            for part in parts:
                cleaned = part.strip().replace("mm", "")
                if cleaned:
                    try:
                        numbers.append(float(cleaned))
                    except ValueError:
                        pass
            if numbers:
                return sum(numbers) / len(numbers)
            else:
                return float("nan")
        else:
            return float("nan")
    
    # Extract and apply average beam width function
    out["racquet_avg_beam_width"] = out["beam_width"].apply(average_beam_width)
    
    ###############
    # MAINS AND CROSSES
    ###############
    
    # Get mains and crosses helper
    def extract_mains_crosses(value):
        # Extract main and cross values, assign to relevant column in series, 
        # and pass series to df
        mains = np.nan
        crosses = np.nan
        
        if isinstance(value, str) and value.strip():
            
            mains_regex = re.search(r'(\d+)\s*Mains', value, re.IGNORECASE)
            crosses_regex = re.search(r'(\d+)\s*Crosses', value, re.IGNORECASE)
            
            if mains_regex:
                mains = float(mains_regex.group(1))
                
            if crosses_regex:
                crosses = float(crosses_regex.group(1))
                
        return pd.Series([mains, crosses])

    # Extract main and cross values and apply to respective columns
    out[["racquet_mains", "racquet_crosses"]] = out["string_pattern"].apply(extract_mains_crosses)
    
    ###############
    # TENSION
    ###############
    
    # Get tension helper
    def extract_tension_bounds(value):
        lower = np.nan
        upper = np.nan
        
        if isinstance(value, str) and value.strip():
            tension_regex = re.search(r'(\d+)\s*-\s*(\d+)', value)
            if tension_regex:
                lower = float(tension_regex.group(1))
                upper = float(tension_regex.group(2))
            
        return pd.Series([lower, upper])

    # Extract and apply tension bounds to new columns
    out[["racquet_tension_lower", "racquet_tension_upper"]] = out["string_tension"].apply(extract_tension_bounds)
    
    return out

def finalize_columns(df:pd.DataFrame) -> pd.DataFrame:
    """Drop non-regexed columns, standardized naming conventions of columns

    Args:
        df (pd.DataFrame): DataFrame with regexed columns

    Returns:
        pd.DataFrame: DataFrame with racquet brand column, junior racquets removed, majority NA columns dropped, 
        string columns transformed, old columns dropped, and column names standardized
    """
    
    out = df.copy()
    drop_cols = ["head_size", "length", "strung_weight", "balance", 
                "beam_width", "string_pattern", "string_tension", "stiffness"]
    
    out.drop(columns = drop_cols, inplace = True)
    out.rename(columns = {"swingweight" : "racquet_swingweight",
                                  "composition" : "racquet_composition",
                                  "power_level" : "racquet_power_level",
                                  "stroke_style" : "racquet_stroke_style",
                                  "swing_speed" : "racquet_swing_speed",
                                  "racquet_colors" : "racquet_colors",
                                  "grip_type" : "racquet_grip_type"},
                        inplace = True)
    
    return out

def clean_raw_data(df:pd.DataFrame) -> pd.DataFrame:
    """Orchestration function that chains together
    cleaning functions to convert raw df to clean df

    Args:
        raw_df (pd.DataFrame): The raw, scraped dataset

    Returns:
        pd.DataFrame: The cleaned dataset
    """
    validate_raw_columns(df = df)
    
    df = drop_name_and_url_nas(df = df)
    df = add_brand_column(df = df)
    df = add_id_column(df = df)
    df = remove_junior_racquets(df = df)
    df = drop_majority_NA_cols(df = df)
    df = extract_numeric_specs(df = df)
    df = finalize_columns(df = df)
    
    return df