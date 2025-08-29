import boto3
import textwrap
from app.utils.logger.logger_util import get_logger
from app.utils.agents_utils.filter_builder import filter_metadata
from app.utils.config.config_util import BR, OPENSEARCH, KNOWLEDGE_BASE

logger = get_logger()

agent_id = KNOWLEDGE_BASE['agent_id']
agent_alias_id = KNOWLEDGE_BASE['agent_alias_id']
KNOWLEDGE_BASE_ID = KNOWLEDGE_BASE['knowledge_base_id']

bedrock_agent = boto3.client(
    service_name='bedrock-agent', 
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=BR['region']
)

bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=BR['region']
)


def run_agent_chatbot(user_input, phase, indicator, section, session_id, memory_id):
    vector_search_config = filter_metadata(phase, section, indicator)

    session_state = {
        "knowledgeBaseConfigurations": [
            {
                "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": vector_search_config
                }
            }
        ]
    }

    logger.info(f"💬 Session State: {session_state}")

    input_text = f"""
User question:
{user_input}

Context:
This question is asked in the context of:
- Phase: {phase}
- Indicator: {indicator}
- Section: {section}

Instructions:
- Use only the retrieved knowledge base content for your answer.
- If the filters are set to "All", interpret the question broadly and include the most relevant information across phases, indicators, and sections.
- If no relevant evidence is found, clearly state it and suggest adjusting the filters or ask the user for clarification.
"""

    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        memoryId=memory_id,
        inputText=input_text,
        endSession=False,
        enableTrace=True,
        sessionState=session_state,
        streamingConfigurations={
            'streamFinalResponse': True
        }
    )
    
    enableTrace=True
    width = 70
    event_stream = response["completion"]
    agent_response = ""

    print(f"User: {textwrap.fill(user_input, width=width)}\n")
    print("Agent:", end=" ", flush=True)

    for event in event_stream:
        if 'chunk' in event:
            chunk_text = event['chunk'].get('bytes', b'').decode('utf-8')
            if not enableTrace:
                print(textwrap.fill(chunk_text, width=width, subsequent_indent='       '), end='', flush=True)
            agent_response += chunk_text
            yield chunk_text
        elif 'trace' in event and enableTrace:
            trace = event['trace']

            if 'trace' in trace:
                trace_details = trace['trace']

                if 'orchestrationTrace' in trace_details:
                    orch_trace = trace_details['orchestrationTrace']

                    if 'invocationInput' in orch_trace:
                        inv_input = orch_trace['invocationInput']
                        print("\nInvocation Input:")
                        print(f"  Type: {inv_input.get('invocationType', 'N/A')}")
                        if 'actionGroupInvocationInput' in inv_input:
                            agi = inv_input['actionGroupInvocationInput']
                            print(f"  Action Group: {agi.get('actionGroupName', 'N/A')}")
                            print(f"  Function: {agi.get('function', 'N/A')}")
                            print(f"  Parameters: {agi.get('parameters', 'N/A')}")

                    if 'rationale' in orch_trace:
                        thought = orch_trace['rationale']['text']
                        print(f"\nAgent's thought process:")
                        print(textwrap.fill(thought, width=width, initial_indent='  ', subsequent_indent='  '))

                    if 'observation' in orch_trace:
                        obs = orch_trace['observation']
                        print("\nObservation:")
                        print(f"  Type: {obs.get('type', 'N/A')}")
                        if 'actionGroupInvocationOutput' in obs:
                            print(f"  Action Group Output: {obs['actionGroupInvocationOutput'].get('text', 'N/A')}")
                        if 'knowledgeBaseLookupOutput' in obs:
                            print("  Knowledge Base Lookup:")
                            for ref in obs['knowledgeBaseLookupOutput'].get('retrievedReferences', []):
                                print(f"    - {ref['content'].get('text', 'N/A')[:50]}...")
                        if 'codeInterpreterInvocationOutput' in obs:
                            cio = obs['codeInterpreterInvocationOutput']
                            print("  Code Interpreter Output:")
                            print(f"    Execution Output: {cio.get('executionOutput', 'N/A')[:50]}...")
                            print(f"    Execution Error: {cio.get('executionError', 'N/A')}")
                            print(f"    Execution Timeout: {cio.get('executionTimeout', 'N/A')}")
                        if 'finalResponse' in obs:
                            final_response = obs['finalResponse']['text']
                            print(f"\nFinal response:")
                            print(
                                textwrap.fill(final_response, width=width, initial_indent='  ', subsequent_indent='  '))

                if 'guardrailTrace' in trace_details:
                    guard_trace = trace_details['guardrailTrace']
                    print("\nGuardrail Trace:")
                    print(f"  Action: {guard_trace.get('action', 'N/A')}")

                    for assessment in guard_trace.get('inputAssessments', []) + guard_trace.get('outputAssessments',
                                                                                                []):
                        if 'contentPolicy' in assessment:
                            for filter in assessment['contentPolicy'].get('filters', []):
                                print(
                                    f"  Content Filter: {filter['type']} (Confidence: {filter['confidence']}, Action: {filter['action']})")

                        if 'sensitiveInformationPolicy' in assessment:
                            for pii in assessment['sensitiveInformationPolicy'].get('piiEntities', []):
                                print(f"  PII Detected: {pii['type']} (Action: {pii['action']})")

    print(f"\n\nSession ID: {response.get('sessionId')}")