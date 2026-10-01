from epistemic_benchmark.utils.io import require

def chat_input_token_count(tokenizer, messages, template_kwargs):
    # Transformers 5 changed return_dict's default. Never count mapping keys.
    tokens = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                           return_dict=False, **template_kwargs)
    require(isinstance(tokens, list) and tokens and all(type(t) is int for t in tokens),
            "Expected a flat, nonempty list of token IDs from the chat template")
    return len(tokens)
