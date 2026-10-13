import pandas as pd

# --------------------------------------------------
# 1. Load job dataset
# --------------------------------------------------
print("Loading job dataset...")

df = pd.read_parquet("jobs_100000_FINAL.parquet")

print(f"Loaded {len(df):,} jobs")


# --------------------------------------------------
# 2. Important columns for our AI job matcher
# --------------------------------------------------
important_columns = [
    "id",
    "company",
    "title",
    "location",
    "work_mode",
    "employment_type",
    "salary_min",
    "salary_max",
    "salary_currency",
    "visa_sponsorship",
    "cpt_status",
    "opt_status",
    "stem_opt_status",
    "citizenship_requirement",
    "job_description",
    "apply_url",
    "source_slug",
]

df = df[important_columns].copy()


# --------------------------------------------------
# 3. Handle missing values
# --------------------------------------------------
text_columns = [
    "company",
    "title",
    "location",
    "work_mode",
    "employment_type",
    "visa_sponsorship",
    "cpt_status",
    "opt_status",
    "stem_opt_status",
    "citizenship_requirement",
    "job_description",
    "apply_url",
    "source_slug",
]

for column in text_columns:
    df[column] = df[column].fillna("").astype(str)


# --------------------------------------------------
# 4. Create text for semantic AI matching
# --------------------------------------------------
df["search_text"] = (
    "Job Title: " + df["title"] +
    "\nCompany: " + df["company"] +
    "\nLocation: " + df["location"] +
    "\nWork Mode: " + df["work_mode"] +
    "\nEmployment Type: " + df["employment_type"] +
    "\nVisa Sponsorship: " + df["visa_sponsorship"] +
    "\nCPT Status: " + df["cpt_status"] +
    "\nOPT Status: " + df["opt_status"] +
    "\nSTEM OPT Status: " + df["stem_opt_status"] +
    "\nCitizenship Requirement: " + df["citizenship_requirement"] +
    "\nJob Description: " + df["job_description"]
)


# --------------------------------------------------
# 5. Remove unusable records
# --------------------------------------------------
df = df[
    (df["title"].str.strip() != "") &
    (df["job_description"].str.strip() != "")
].copy()

df = df.drop_duplicates(subset=["id"])


# --------------------------------------------------
# 6. Save cleaned dataset
# --------------------------------------------------
output_file = "jobs_cleaned.parquet"

df.to_parquet(output_file, index=False)


# --------------------------------------------------
# 7. Display results
# --------------------------------------------------
print("\n--------------------------------")
print("JOB DATA PREPARATION COMPLETE")
print("--------------------------------")

print(f"Clean jobs: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(f"Saved as: {output_file}")

print("\nSample job:")
print("Title:", df.iloc[0]["title"])
print("Company:", df.iloc[0]["company"])
print("Location:", df.iloc[0]["location"])
print("Apply URL:", df.iloc[0]["apply_url"])

print("\nSearch text preview:")
print(df.iloc[0]["search_text"][:500])