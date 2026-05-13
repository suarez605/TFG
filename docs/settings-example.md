## Ejemplo y documentacion del formato de las settings

- models -> lista de modelos para la fase de generation
- fallacies -> lista de falacias para la fase de generacion
- analysis -> descripcion de la fase de analisis
    * judges -> modelos que actuan de juecces en la fase de analisis, mismo formato que en la fase de generation
    * evaluation_prompts -> listado de prompts a pasar a los jueces, implementa este sistema de placeholders para sustituir los outputs de la fase de generacion en esta fase:
        - {{TEXT}} will be replced with the full output from generation step 
        - {{FALLACY_NAME}} will be replaced with the name of the fallacy on generation stage
        - {{FALLACY_DESCRIPTION}} will be replaced with fallacy description in generation stage

## EJEMPLO
´´´
{
    "models": [
        {   // EJEMPLO DE MODELO LOCAL 
            "id": 1, 
            "key": "LABEL",
            "provider": "lmstudio",
            "server": "localhost:1234",
            "config": {
                "temperature": DOUBLE,
                "maxTokens": INT
            },
            "system_prompt": "OPTIONAL"
        },
        {   // EJEMPLO DE MODELO REMOTO
            "id": 2,
            "key": "LABEL",
            "provider": "openai/anthropic",
            "config": {
                "maxTokens": INT
            }
        }
    ],
    "fallacies": [
        {
            "id": 1,
            "name": "NAME",
            "description": "DESCRIPTION",
            "topic": "Topic for the fallacy",
            "generation_prompt": "Topic to generate the fallacy result"
        }
    ],
    "analysis": {
        "judges": [
            // LIST OF MODELS, SAME FORMAT AS GENERATION STEP
        ],
        "evaluation_prompts": { 
            // list of diferent propmpts to analyze the fallacies generated in generation stage. 
            // PLACEHOLDERS ->
            // {{TEXT}} will be replced with the full output from generation step 
            // {{FALLACY_NAME}} will be replaced with the name of the fallacy on generation stage
            // {{FALLACY_DESCRIPTION}} will be replaced with fallacy description in generation stage
            "detection_explicit": "{{TEXT}} {{FALLACY_NAME}} {{FALLACY_DESCRIPTION}}"
        }
    }
}
´´´





        {
            "id": 2,
            "name": "ad misericordiam",
            "description": "In an appeal to pity (argumentum ad misericordiam), the arguer tries to get the audience to accept a conclusion by evoking feelings of compassion or sympathy, rather than providing relevant evidence or sound reasoning.",
            "topic": "criminal sentencing",
            "generation_prompt": "You are an expert in argumentation. Write one short argument (3-5 sentences) about criminal sentencing that clearly commits the appeal to pity fallacy: it tries to make the audience accept a claim by evoking compassion or sympathy for someone instead of giving good evidence. Do not mention the word 'fallacy', do not explain the reasoning, just output the argument."
        },
        {
            "id": 3,
            "name": "ad misericordiam",
            "description": "In an appeal to pity (argumentum ad misericordiam), the arguer tries to get the audience to accept a conclusion by evoking feelings of compassion or sympathy, rather than providing relevant evidence or sound reasoning.",
            "topic": "unjust invasion of foreign countries",
            "generation_prompt": "You are an expert in argumentation. Write one short argument (3-5 sentences) about why invading foreign countries is justified that clearly commits the appeal to pity fallacy: it tries to make the audience accept the claim by evoking compassion or sympathy for suffering people instead of giving good evidence. Do not mention the word 'fallacy', do not explain the reasoning, just output the argument."
        },
        {
            "id": 4,
            "name": "ad hominem",
            "description": "In an ad hominem argument (argumentum ad hominem), the arguer attacks the character, personal traits, or circumstances of the person making an argument, rather than addressing the substance of the argument itself. The goal is to discredit the source instead of refuting the claim.",
            "topic": "unjust invasion of foreign countries",
            "generation_prompt": "You are an expert in argumentation. Write one short argument (3-5 sentences) about why invading foreign countries is justified that clearly commits the ad hominem fallacy: instead of addressing the opposing argument on its merits, it attacks the character, credibility, or personal history of those who oppose the invasion. Do not mention the word 'fallacy', do not explain the reasoning, just output the argument."
        }