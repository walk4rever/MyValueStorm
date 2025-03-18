"""
Command-line interface for MyValueStorm with S3 storage support.
"""

import argparse
import os
import sys
from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.result_manager import ResultManager

def main():
    parser = argparse.ArgumentParser(description="STORM Research Assistant")
    parser.add_argument("--topic", type=str, required=True, help="Research topic")
    parser.add_argument("--output-dir", type=str, default="./results", help="Output directory")
    parser.add_argument("--model-provider", type=str, default="bedrock", choices=["bedrock", "openai", "anthropic"], help="Model provider")
    parser.add_argument("--temperature", type=float, default=0.7, help="Model temperature")
    parser.add_argument("--top-p", type=float, default=0.9, help="Model top-p")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Maximum tokens")
    parser.add_argument("--num-search-results", type=int, default=10, help="Number of search results")
    parser.add_argument("--use-s3", action="store_true", help="Use S3 storage")
    parser.add_argument("--s3-bucket", type=str, default="mystorm-results", help="S3 bucket name")
    parser.add_argument("--s3-region", type=str, default=None, help="AWS region for S3")
    parser.add_argument("--skip-research", action="store_true", help="Skip research step")
    parser.add_argument("--skip-outline", action="store_true", help="Skip outline generation step")
    parser.add_argument("--skip-article", action="store_true", help="Skip article generation step")
    parser.add_argument("--skip-polish", action="store_true", help="Skip article polishing step")
    
    args = parser.parse_args()
    
    # Check for Tavily API key
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_api_key:
        print("Error: TAVILY_API_KEY environment variable not found. Please set it before running.")
        sys.exit(1)
    
    # Initialize result manager
    result_manager = ResultManager(
        base_dir=args.output_dir,
        use_s3=args.use_s3,
        s3_bucket=args.s3_bucket,
        s3_region=args.s3_region
    )
    
    # Format topic for directory name
    topic_dir_name = args.topic.lower().replace(" ", "_").replace("/", "_")
    full_output_path = result_manager.get_topic_dir(args.topic)
    os.makedirs(full_output_path, exist_ok=True)
    
    # Configure STORM
    lm_configs = STORMWikiLMConfigs()
    
    # Model configuration based on provider
    model_kwargs = {
        "temperature": args.temperature,
        "top_p": args.top_p,
    }
    
    # Initialize model variables
    conv_simulator_lm = None
    question_asker_lm = None
    outline_gen_lm = None
    article_gen_lm = None
    article_polish_lm = None
    
    print(f"Using model provider: {args.model_provider}")
    
    if args.model_provider == "bedrock":
        bedrock_model = "anthropic.claude-3-sonnet-20240229-v1:0"
        model_name = "bedrock/" + bedrock_model
        
        # Set up all the required LMs
        conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
        article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
        article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
        
    elif args.model_provider == "openai":
        model_name = "gpt-4-turbo"
        
        # Set up all the required LMs
        conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
        article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
        article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
        
    elif args.model_provider == "anthropic":
        model_name = "claude-3-sonnet-20240229"
        
        # Set up all the required LMs
        conv_simulator_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        question_asker_lm = LitellmModel(model=model_name, max_tokens=500, **model_kwargs)
        outline_gen_lm = LitellmModel(model=model_name, max_tokens=400, **model_kwargs)
        article_gen_lm = LitellmModel(model=model_name, max_tokens=700, **model_kwargs)
        article_polish_lm = LitellmModel(model=model_name, max_tokens=4000, **model_kwargs)
    
    # Set the LMs in the config
    lm_configs.set_conv_simulator_lm(conv_simulator_lm)
    lm_configs.set_question_asker_lm(question_asker_lm)
    lm_configs.set_outline_gen_lm(outline_gen_lm)
    lm_configs.set_article_gen_lm(article_gen_lm)
    lm_configs.set_article_polish_lm(article_polish_lm)
    
    # Configure retrieval model
    print("Setting up retrieval model...")
    rm = TavilySearchRM(
        tavily_search_api_key=tavily_api_key,
        k=args.num_search_results,
        include_raw_content=True
    )
    
    # Set up STORM arguments
    storm_args = STORMWikiRunnerArguments(
        output_dir=args.output_dir,
        search_top_k=args.num_search_results
    )
    
    # Initialize STORM runner
    print("Initializing STORM runner...")
    runner = STORMWikiRunner(
        args=storm_args,
        lm_configs=lm_configs,
        rm=rm
    )
    
    # Execute STORM
    print(f"Starting STORM process for topic: {args.topic}")
    runner.run(
        topic=args.topic,
        do_research=not args.skip_research,
        do_generate_outline=not args.skip_outline,
        do_generate_article=not args.skip_article,
        do_polish_article=not args.skip_polish
    )
    
    # Upload results to S3 if enabled
    if args.use_s3:
        print("Uploading results to S3...")
        if result_manager.upload_topic_results(args.topic):
            print("Results uploaded to S3 successfully!")
        else:
            print("Failed to upload results to S3")
    
    print("STORM process completed successfully!")

if __name__ == "__main__":
    main()
