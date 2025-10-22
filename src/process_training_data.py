"""
Training Data Processing Utility

This script helps process the exported JSON files from the AI Query interface
into formats suitable for fine-tuning language models.

Usage:
    python process_training_data.py --input_dir ./training_data --output_file dataset.jsonl
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import re


class TrainingDataProcessor:
    """Process exported AI query results into fine-tuning datasets."""

    def __init__(self, input_dir: str, output_file: str = None):
        self.input_dir = Path(input_dir)
        self.output_file = output_file
        self.good_examples = []
        self.bad_examples = []

    def load_examples(self):
        """Load all JSON files from input directory."""
        print(f"📂 Loading examples from {self.input_dir}...")

        good_dir = self.input_dir / "good_examples"
        bad_dir = self.input_dir / "bad_examples"

        # Load good examples
        if good_dir.exists():
            for file in good_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.good_examples.append(data)
                except Exception as e:
                    print(f"⚠️  Error loading {file}: {e}")

        # Load bad examples
        if bad_dir.exists():
            for file in bad_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.bad_examples.append(data)
                except Exception as e:
                    print(f"⚠️  Error loading {file}: {e}")

        print(f"✅ Loaded {len(self.good_examples)} good examples")
        print(f"✅ Loaded {len(self.bad_examples)} bad examples")

    def clean_sql(self, sql: str) -> str:
        """Clean and normalize SQL query."""
        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql)
        sql = sql.strip()
        return sql

    def convert_to_llama_format(self) -> List[Dict[str, Any]]:
        """
        Convert examples to Llama fine-tuning format.

        Format:
        {
            "instruction": "...",
            "input": "...",
            "output": "..."
        }
        """
        dataset = []

        # Process good examples
        for example in self.good_examples:
            entry = {
                "instruction": (
                    "Generate a SQLite query for the following natural language request. "
                    "Use proper SQLite syntax, not PostgreSQL. "
                    "Include appropriate JOINs when referencing related tables. "
                    "Format dates as YYYY-MM."
                ),
                "input": example['user_query'],
                "output": self.clean_sql(example['generated_sql']),
                "metadata": {
                    "type": "good_example",
                    "timestamp": example.get('timestamp'),
                    "row_count": example.get('row_count'),
                    "success": True
                }
            }
            dataset.append(entry)

        # Process bad examples with corrections
        for example in self.bad_examples:
            # Create a "what not to do" example
            entry = {
                "instruction": (
                    "Generate a SQLite query for the following natural language request. "
                    "Use proper SQLite syntax, not PostgreSQL. "
                    "Include appropriate JOINs when referencing related tables. "
                    "Format dates as YYYY-MM."
                ),
                "input": example['user_query'],
                "output": f"ERROR: {example.get('issue_description', 'Unknown error')}\n"
                         f"INCORRECT SQL: {self.clean_sql(example['generated_sql'])}\n"
                         f"CORRECTION NEEDED: Use SQLite syntax, proper JOINs, and YYYY-MM date format.",
                "metadata": {
                    "type": "bad_example",
                    "timestamp": example.get('timestamp'),
                    "issue": example.get('issue_description'),
                    "success": False
                }
            }
            dataset.append(entry)

        return dataset

    def convert_to_alpaca_format(self) -> List[Dict[str, Any]]:
        """
        Convert examples to Alpaca fine-tuning format.

        Format:
        {
            "instruction": "...",
            "input": "...",
            "output": "..."
        }
        """
        # Alpaca format is similar to Llama format
        return self.convert_to_llama_format()

    def convert_to_openai_format(self) -> List[Dict[str, Any]]:
        """
        Convert examples to OpenAI fine-tuning format.

        Format:
        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
        """
        dataset = []

        system_message = (
            "You are a SQLite query generator. Generate valid SQLite queries "
            "from natural language requests. Always use SQLite syntax, include "
            "appropriate JOINs when referencing related tables, and format dates as YYYY-MM."
        )

        # Process good examples
        for example in self.good_examples:
            entry = {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": example['user_query']},
                    {"role": "assistant", "content": self.clean_sql(example['generated_sql'])}
                ],
                "metadata": {
                    "type": "good_example",
                    "timestamp": example.get('timestamp'),
                    "success": True
                }
            }
            dataset.append(entry)

        # Process bad examples
        for example in self.bad_examples:
            correction = (
                f"I apologize, but that query has an error: {example.get('issue_description', 'Unknown error')}. "
                f"The correct approach would be to use SQLite syntax, proper JOINs, and YYYY-MM date format. "
                f"Let me provide a corrected version."
            )

            entry = {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": example['user_query']},
                    {"role": "assistant", "content": correction}
                ],
                "metadata": {
                    "type": "bad_example_correction",
                    "timestamp": example.get('timestamp'),
                    "original_error": example.get('issue_description'),
                    "success": False
                }
            }
            dataset.append(entry)

        return dataset

    def generate_statistics(self):
        """Generate statistics about the training dataset."""
        print("\n" + "=" * 60)
        print("TRAINING DATA STATISTICS")
        print("=" * 60)

        print(f"\n📊 Dataset Composition:")
        print(f"   Good Examples: {len(self.good_examples)}")
        print(f"   Bad Examples:  {len(self.bad_examples)}")
        print(f"   Total:         {len(self.good_examples) + len(self.bad_examples)}")

        # Analyze query types
        query_keywords = {
            'list': 0,
            'show': 0,
            'loading': 0,
            'product': 0,
            'month': 0,
            'compare': 0,
            'resource': 0,
            'station': 0
        }

        all_examples = self.good_examples + self.bad_examples
        for example in all_examples:
            query = example['user_query'].lower()
            for keyword in query_keywords:
                if keyword in query:
                    query_keywords[keyword] += 1

        print(f"\n🔍 Query Keyword Analysis:")
        for keyword, count in sorted(query_keywords.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"   {keyword}: {count}")

        # Success rate from good examples
        if self.good_examples:
            successful = sum(1 for e in self.good_examples if e.get('sql_execution_success', False))
            success_rate = (successful / len(self.good_examples)) * 100
            print(f"\n✅ Success Rate (Good Examples): {success_rate:.1f}%")

        # Common issues from bad examples
        if self.bad_examples:
            print(f"\n❌ Common Issues (Bad Examples):")
            issues = {}
            for example in self.bad_examples:
                issue = example.get('issue_description', 'Unknown')
                issues[issue] = issues.get(issue, 0) + 1

            for issue, count in sorted(issues.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {issue}: {count} occurrence(s)")

        # Date range
        timestamps = [e.get('timestamp') for e in all_examples if e.get('timestamp')]
        if timestamps:
            timestamps.sort()
            print(f"\n📅 Data Collection Period:")
            print(f"   First: {timestamps[0]}")
            print(f"   Last:  {timestamps[-1]}")

        print("\n" + "=" * 60 + "\n")

    def save_dataset(self, format_type: str = 'llama'):
        """Save processed dataset to file."""
        if not self.output_file:
            self.output_file = f"training_data_{format_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

        # Convert to specified format
        if format_type == 'llama':
            dataset = self.convert_to_llama_format()
        elif format_type == 'alpaca':
            dataset = self.convert_to_alpaca_format()
        elif format_type == 'openai':
            dataset = self.convert_to_openai_format()
        else:
            raise ValueError(f"Unknown format: {format_type}")

        # Save as JSONL (one JSON object per line)
        output_path = Path(self.output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f"✅ Saved {len(dataset)} training examples to {output_path}")

    def export_summary_report(self):
        """Export a summary report of the training data."""
        report_file = self.input_dir / "training_data_summary.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("TRAINING DATA SUMMARY REPORT\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input Directory: {self.input_dir}\n\n")

            f.write(f"Good Examples: {len(self.good_examples)}\n")
            f.write(f"Bad Examples: {len(self.bad_examples)}\n")
            f.write(f"Total: {len(self.good_examples) + len(self.bad_examples)}\n\n")

            f.write("=" * 60 + "\n\n")

            # List all good examples
            f.write("GOOD EXAMPLES:\n")
            f.write("-" * 60 + "\n")
            for i, example in enumerate(self.good_examples, 1):
                f.write(f"\n{i}. {example['user_query']}\n")
                f.write(f"   Timestamp: {example.get('timestamp', 'N/A')}\n")
                f.write(f"   Row Count: {example.get('row_count', 'N/A')}\n")
                f.write(f"   SQL: {self.clean_sql(example['generated_sql'])[:100]}...\n")

            # List all bad examples
            f.write("\n\nBAD EXAMPLES:\n")
            f.write("-" * 60 + "\n")
            for i, example in enumerate(self.bad_examples, 1):
                f.write(f"\n{i}. {example['user_query']}\n")
                f.write(f"   Timestamp: {example.get('timestamp', 'N/A')}\n")
                f.write(f"   Issue: {example.get('issue_description', 'N/A')}\n")
                f.write(f"   SQL: {self.clean_sql(example['generated_sql'])[:100]}...\n")

        print(f"📝 Summary report saved to {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Process AI query training data exports'
    )
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Directory containing good_examples/ and bad_examples/ folders'
    )
    parser.add_argument(
        '--output_file',
        type=str,
        help='Output file name (default: auto-generated)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['llama', 'alpaca', 'openai'],
        default='llama',
        help='Output format (default: llama)'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only generate statistics, do not create training file'
    )

    args = parser.parse_args()

    # Initialize processor
    processor = TrainingDataProcessor(args.input_dir, args.output_file)

    # Load examples
    processor.load_examples()

    if not processor.good_examples and not processor.bad_examples:
        print("❌ No examples found. Make sure you have good_examples/ and/or bad_examples/ folders.")
        return

    # Generate statistics
    processor.generate_statistics()

    # Export summary report
    processor.export_summary_report()

    # Save dataset (unless stats-only)
    if not args.stats_only:
        processor.save_dataset(format_type=args.format)
        print(f"\n✅ Training dataset ready for fine-tuning!")
        print(f"   Format: {args.format}")
        print(f"   Use this file with your fine-tuning framework")


if __name__ == '__main__':
    main()