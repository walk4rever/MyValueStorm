"""
STORM Wiki pipeline powered by Amazon Bedrock Claude and a search engine.
You need to set up the following environment variables to run this script:
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_REGION: AWS region where Bedrock is available (e.g., us-west-2)
    - TAVILY_API_KEY: Tavily API key for search

Output will be structured as below
args.output_dir/
    topic_name/  # topic_name will follow convention of underscore-connected topic name w/o space and slash
        conversation_log.json           # Log of information-seeking conversation
        raw_search_results.json         # Raw search results from search engine
        direct_gen_outline.txt          # Outline directly generated with LLM's parametric knowledge
        storm_gen_outline.txt           # Outline refined with collected information
        url_to_info.json                # Sources that are used in the final article
        storm_gen_article.txt           # Final article generated
        storm_gen_article_polished.txt  # Polished final article (if args.do_polish_article is True)
"""

import os
from argparse import ArgumentParser

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM


def main(args):
    lm_configs = STORMWikiLMConfigs()
    
    # Print available environment variables for debugging
    print(f"AWS_REGION: {os.getenv('AWS_REGION')}")
    print(f"TAVILY_API_KEY exists: {os.getenv('TAVILY_API_KEY') is not None}")
    
    # Common parameters for LitellmModel
    bedrock_kwargs = {
        "temperature": 1.0,
        "top_p": 0.9,
    }

    # Test if the model works with direct litellm call
    try:
        import litellm
        litellm.set_verbose = True
        print(f"Testing Bedrock model access...")
        
        # Use standard Bedrock model IDs - these are the most commonly available
        #bedrock_model = "anthropic.claude-v2"
        bedrock_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        
        response = litellm.completion(
            model="bedrock/" + bedrock_model,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10
        )
        print("Success! Model is accessible.")
        print(response)
    except Exception as e:
        print(f"Error testing model: {e}")
        print("Please check your AWS credentials and model access.")
        return
    
    # If the test passes, set up the models for STORM
    conv_simulator_lm = LitellmModel(model="bedrock/" + bedrock_model, max_tokens=500, **bedrock_kwargs)
    question_asker_lm = LitellmModel(model="bedrock/" + bedrock_model, max_tokens=500, **bedrock_kwargs)
    outline_gen_lm = LitellmModel(model="bedrock/" + bedrock_model, max_tokens=400, **bedrock_kwargs)
    article_gen_lm = LitellmModel(model="bedrock/" + bedrock_model, max_tokens=700, **bedrock_kwargs)
    article_polish_lm = LitellmModel(model="bedrock/" + bedrock_model, max_tokens=4000, **bedrock_kwargs)

    lm_configs.set_conv_simulator_lm(conv_simulator_lm)
    lm_configs.set_question_asker_lm(question_asker_lm)
    lm_configs.set_outline_gen_lm(outline_gen_lm)
    lm_configs.set_article_gen_lm(article_gen_lm)
    lm_configs.set_article_polish_lm(article_polish_lm)

    engine_args = STORMWikiRunnerArguments(
        output_dir=args.output_dir,
        max_conv_turn=args.max_conv_turn,
        max_perspective=args.max_perspective,
        search_top_k=args.search_top_k,
        max_thread_num=args.max_thread_num,
    )

    # Use Tavily as the retrieval module
    rm = TavilySearchRM(
        tavily_search_api_key=os.getenv("TAVILY_API_KEY"),
        k=engine_args.search_top_k,
        include_raw_content=True,
    )
    
    # Test Tavily search before proceeding
    print("Testing Tavily search...")
    try:
        test_results = rm.forward("test query")
        print(f"Tavily test successful, found {len(test_results)} results")
    except Exception as e:
        print(f"Tavily test failed: {e}")
        print("Please check your Tavily API key and try again.")
        exit(1)

    runner = STORMWikiRunner(engine_args, lm_configs, rm)

    topic = input("Topic: ")
    runner.run(
        topic=topic,
        do_research=args.do_research,
        do_generate_outline=args.do_generate_outline,
        do_generate_article=args.do_generate_article,
        do_polish_article=args.do_polish_article,
    )
    runner.post_run()
    runner.summary()


if __name__ == "__main__":
    parser = ArgumentParser()
    # global arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results/bedrock",
        help="Directory to store the outputs.",
    )
    parser.add_argument(
        "--max-thread-num",
        type=int,
        default=3,
        help="Maximum number of threads to use.",
    )
    # stage of the pipeline
    parser.add_argument(
        "--do-research",
        action="store_true",
        help="If True, simulate conversation to research the topic; otherwise, load the results.",
    )
    parser.add_argument(
        "--do-generate-outline",
        action="store_true",
        help="If True, generate an outline for the topic; otherwise, load the results.",
    )
    parser.add_argument(
        "--do-generate-article",
        action="store_true",
        help="If True, generate an article for the topic; otherwise, load the results.",
    )
    parser.add_argument(
        "--do-polish-article",
        action="store_true",
        help="If True, polish the article by adding a summarization section.",
    )
    # hyperparameters for the pre-writing stage
    parser.add_argument(
        "--max-conv-turn",
        type=int,
        default=3,
        help="Maximum number of questions in conversational question asking.",
    )
    parser.add_argument(
        "--max-perspective",
        type=int,
        default=3,
        help="Maximum number of perspectives to consider in perspective-guided question asking.",
    )
    parser.add_argument(
        "--search-top-k",
        type=int,
        default=3,
        help="Top k search results to consider for each search query.",
    )

    main(parser.parse_args())
