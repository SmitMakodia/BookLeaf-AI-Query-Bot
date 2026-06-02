from langgraph.graph import StateGraph, END
from app.schemas.agent import AgentState
from app.agent.nodes import (
    identity_node, intent_node, retrieval_node, generate_node, confidence_node,
)
from app.db.repository import Repository
import uuid

def _route_after_confidence(state: AgentState) -> str:
    return "escalate" if state.is_escalated else END

async def _escalate_node(state: AgentState) -> AgentState:
    if state.final_response:
        state.final_response = (
            "I found some information, but I want to make sure it is fully accurate. "
            "A BookLeaf team member will follow up with you shortly.\n\n"
            + state.final_response
        )
    else:
        state.final_response = (
            "I could not find the information you need right now. "
            "A BookLeaf team member will contact you within 2 hours."
        )
    return state

class AgentWorkflow:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        async def node_identity(state):   return await identity_node(state, self.repo)
        async def node_intent(state):     return await intent_node(state)
        async def node_retrieve(state):   return await retrieval_node(state, self.repo)
        async def node_generate(state):   return await generate_node(state)
        async def node_confidence(state): return await confidence_node(state)
        async def node_escalate(state):   return await _escalate_node(state)

        workflow.add_node("identity",   node_identity)
        workflow.add_node("intent",     node_intent)
        workflow.add_node("retrieve",   node_retrieve)
        workflow.add_node("generate",   node_generate)
        workflow.add_node("confidence", node_confidence)
        workflow.add_node("escalate",   node_escalate)

        workflow.set_entry_point("identity")
        workflow.add_edge("identity",   "intent")
        workflow.add_edge("intent",     "retrieve")
        workflow.add_edge("retrieve",   "generate")
        workflow.add_edge("generate",   "confidence")
        workflow.add_conditional_edges("confidence", _route_after_confidence,
                                       {"escalate": "escalate", END: END})
        workflow.add_edge("escalate", END)

        return workflow.compile()

    async def invoke(self, query: str, channel: str, identifier: str) -> AgentState:
        state = AgentState(
            correlation_id=str(uuid.uuid4()),
            query=query,
            channel=channel,
            identifier=identifier,
        )
        result = await self.graph.ainvoke(state)
        return AgentState(**result)
