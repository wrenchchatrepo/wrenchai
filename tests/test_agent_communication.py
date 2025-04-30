"""
Integration tests for agent communication patterns.

These tests verify the communication patterns between different agents in the system.
"""
import unittest
import asyncio
from unittest.mock import MagicMock, patch
# Add unit test path for imports
import sys
import os
from pathlib import Path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import directly from files to avoid dependency issues in testing
from core.tools.message_broker import MessageBroker, Message, MessageType, MessagePriority
from core.agents.messaging import MessagingCapability


class Topic:
    """Topic for pub-sub messaging."""
    
    def __init__(self, name: str):
        self.name = name
        
    def __str__(self):
        return self.name
        
    def __eq__(self, other):
        if isinstance(other, Topic):
            return self.name == other.name
        return False


from core.agents.communication_patterns import (
    RequestResponse,
    PubSub,
    EventBus,
    WorkflowMessaging,
    ConditionalRouter,
    AgentPool
)


class TestAgentCommunication(unittest.TestCase):
    def setUp(self):
        self.broker = MessageBroker()
        
    def test_direct_messaging(self):
        sender_agent = MagicMock()
        sender_agent.id = "sender"
        receiver_agent = MagicMock()
        receiver_agent.id = "receiver"
        
        sender_messaging = MessagingCapability(sender_agent, self.broker)
        receiver_messaging = MessagingCapability(receiver_agent, self.broker)
        
        # Register message handling for receiver
        received_messages = []
        receiver_messaging.register_message_handler(lambda msg: received_messages.append(msg))
        
        # Send a direct message
        test_message = Message(
            sender="sender",
            recipient="receiver",
            content={"data": "test_content"},
            type="TEST"
        )
        sender_messaging.send_message(test_message)
        
        # Check if message was received
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].content["data"], "test_content")
        
    def test_broadcast_messaging(self):
        sender_agent = MagicMock()
        sender_agent.id = "broadcaster"
        
        receiver1_agent = MagicMock()
        receiver1_agent.id = "receiver1"
        receiver2_agent = MagicMock()
        receiver2_agent.id = "receiver2"
        
        # Set up messaging capabilities
        sender_messaging = MessagingCapability(sender_agent, self.broker)
        receiver1_messaging = MessagingCapability(receiver1_agent, self.broker)
        receiver2_messaging = MessagingCapability(receiver2_agent, self.broker)
        
        # Register handlers
        receiver1_messages = []
        receiver2_messages = []
        receiver1_messaging.register_handler(lambda msg: receiver1_messages.append(msg))
        receiver2_messaging.register_handler(lambda msg: receiver2_messages.append(msg))
        
        # Broadcast a message
        broadcast_message = Message(
            sender_id="broadcaster",
            receiver_id=None,  # None indicates broadcast
            content={"announcement": "Important broadcast"},
            message_type="BROADCAST"
        )
        sender_messaging.broadcast_message(broadcast_message)
        
        # Both receivers should get the message
        self.assertEqual(len(receiver1_messages), 1)
        self.assertEqual(len(receiver2_messages), 1)
        self.assertEqual(receiver1_messages[0].content["announcement"], "Important broadcast")
        self.assertEqual(receiver2_messages[0].content["announcement"], "Important broadcast")
    
    def test_request_response_pattern(self):
        # Test the RequestResponse communication pattern
        requester = MagicMock()
        requester.id = "requester"
        responder = MagicMock()
        responder.id = "responder"
        
        requester_messaging = MessagingCapability(requester, self.broker)
        responder_messaging = MessagingCapability(responder, self.broker)
        
        # Create a request-response pattern
        rr_pattern = RequestResponse(requester_messaging)
        
        # Set up the responder handler
        async def handle_request(request):
            if request.content.get("question") == "What is 2+2?":
                return Message(
                    sender=responder.id,
                    recipient=request.sender,
                    content={"answer": 4},
                    type="RESPONSE",
                    reply_to=request.id
                )
            return None
        
        responder_messaging.register_handler(handle_request)
        
        # Send a request and get the response
        request = Message(
            sender=requester.id,
            recipient=responder.id,
            content={"question": "What is 2+2?"},
            type="REQUEST"
        )
        
        # Use asyncio to run the coroutine
        response = asyncio.run(rr_pattern.request(request))
        
        # Check the response
        self.assertIsNotNone(response)
        self.assertEqual(response.content["answer"], 4)
    
    def test_pubsub_pattern(self):
        # Test the PubSub communication pattern
        publisher = MagicMock()
        publisher.id = "publisher"
        subscriber1 = MagicMock()
        subscriber1.id = "subscriber1"
        subscriber2 = MagicMock()
        subscriber2.id = "subscriber2"
        
        publisher_messaging = MessagingCapability(publisher, self.broker)
        subscriber1_messaging = MessagingCapability(subscriber1, self.broker)
        subscriber2_messaging = MessagingCapability(subscriber2, self.broker)
        
        # Create a pub-sub pattern
        pubsub = PubSub(self.broker)
        
        # Set up subscribers
        subscriber1_messages = []
        subscriber2_messages = []
        
        async def handle_sub1(msg):
            subscriber1_messages.append(msg)
            
        async def handle_sub2(msg):
            subscriber2_messages.append(msg)
        
        # Subscribe to topics
        weather_topic = Topic("weather")
        sports_topic = Topic("sports")
        
        pubsub.subscribe(subscriber1_messaging, weather_topic, handle_sub1)
        pubsub.subscribe(subscriber1_messaging, sports_topic, handle_sub1)
        pubsub.subscribe(subscriber2_messaging, weather_topic, handle_sub2)
        # Note: subscriber2 doesn't subscribe to sports
        
        # Publish messages to topics
        weather_message = Message(
            sender_id=publisher.id,
            content={"forecast": "sunny"},
            message_type="PUBLICATION",
            topic=weather_topic
        )
        
        sports_message = Message(
            sender_id=publisher.id,
            content={"event": "championship"},
            message_type="PUBLICATION",
            topic=sports_topic
        )
        
        asyncio.run(pubsub.publish(publisher_messaging, weather_message))
        asyncio.run(pubsub.publish(publisher_messaging, sports_message))
        
        # Check that subscribers received appropriate messages
        self.assertEqual(len(subscriber1_messages), 2)  # Subscribed to both topics
        self.assertEqual(len(subscriber2_messages), 1)  # Only subscribed to weather
        
        # Verify message content
        weather_received = any(msg.content.get("forecast") == "sunny" for msg in subscriber1_messages)
        sports_received = any(msg.content.get("event") == "championship" for msg in subscriber1_messages)
        self.assertTrue(weather_received)
        self.assertTrue(sports_received)
        
        # Subscriber2 should only have weather
        self.assertEqual(subscriber2_messages[0].content["forecast"], "sunny")
        
    def test_event_bus_pattern(self):
        # Test the EventBus communication pattern
        agent1 = MagicMock()
        agent1.id = "agent1"
        agent2 = MagicMock()
        agent2.id = "agent2"
        agent3 = MagicMock()
        agent3.id = "agent3"
        
        agent1_messaging = MessagingCapability(agent1, self.broker)
        agent2_messaging = MessagingCapability(agent2, self.broker)
        agent3_messaging = MessagingCapability(agent3, self.broker)
        
        # Create event bus
        event_bus = EventBus(self.broker)
        
        # Register event handlers
        agent2_code_events = []
        agent2_doc_events = []
        agent3_code_events = []
        
        async def agent2_code_handler(event):
            agent2_code_events.append(event)
            
        async def agent2_doc_handler(event):
            agent2_doc_events.append(event)
            
        async def agent3_code_handler(event):
            agent3_code_events.append(event)
        
        # Register handlers for event types
        event_bus.register_handler(agent2_messaging, "code_change", agent2_code_handler)
        event_bus.register_handler(agent2_messaging, "doc_update", agent2_doc_handler)
        event_bus.register_handler(agent3_messaging, "code_change", agent3_code_handler)
        
        # Publish events
        code_event = Message(
            sender_id=agent1.id,
            content={"file": "main.py", "change": "Added new function"},
            message_type="EVENT",
            event_type="code_change"
        )
        
        doc_event = Message(
            sender_id=agent1.id,
            content={"file": "README.md", "change": "Updated installation section"},
            message_type="EVENT",
            event_type="doc_update"
        )
        
        asyncio.run(event_bus.publish_event(agent1_messaging, code_event))
        asyncio.run(event_bus.publish_event(agent1_messaging, doc_event))
        
        # Verify event distribution
        self.assertEqual(len(agent2_code_events), 1)
        self.assertEqual(len(agent2_doc_events), 1)
        self.assertEqual(len(agent3_code_events), 1)
        
        self.assertEqual(agent2_code_events[0].content["file"], "main.py")
        self.assertEqual(agent2_doc_events[0].content["file"], "README.md")
        self.assertEqual(agent3_code_events[0].content["file"], "main.py")
    
    def test_workflow_messaging_pattern(self):
        # Test the WorkflowMessaging pattern
        coordinator = MagicMock()
        coordinator.id = "coordinator"
        worker1 = MagicMock()
        worker1.id = "worker1"
        worker2 = MagicMock()
        worker2.id = "worker2"
        
        coordinator_messaging = MessagingCapability(coordinator, self.broker)
        worker1_messaging = MessagingCapability(worker1, self.broker)
        worker2_messaging = MessagingCapability(worker2, self.broker)
        
        # Create workflow messaging
        workflow = WorkflowMessaging(coordinator_messaging, [worker1_messaging, worker2_messaging])
        
        # Register task handlers
        async def worker1_task_handler(task):
            if task.content["task_type"] == "process_data":
                return Message(
                    sender_id=worker1.id,
                    receiver_id=coordinator.id,
                    content={
                        "task_id": task.content["task_id"],
                        "result": "processed data",
                        "status": "completed"
                    },
                    message_type="TASK_RESULT",
                    correlation_id=task.id
                )
            return None
            
        async def worker2_task_handler(task):
            if task.content["task_type"] == "generate_report":
                return Message(
                    sender_id=worker2.id,
                    receiver_id=coordinator.id,
                    content={
                        "task_id": task.content["task_id"],
                        "result": "report generated",
                        "status": "completed"
                    },
                    message_type="TASK_RESULT",
                    correlation_id=task.id
                )
            return None
        
        worker1_messaging.register_handler(worker1_task_handler)
        worker2_messaging.register_handler(worker2_task_handler)
        
        # Create a workflow with tasks
        tasks = [
            Message(
                sender_id=coordinator.id,
                receiver_id=worker1.id,
                content={"task_id": "1", "task_type": "process_data"},
                message_type="TASK"
            ),
            Message(
                sender_id=coordinator.id,
                receiver_id=worker2.id,
                content={"task_id": "2", "task_type": "generate_report"},
                message_type="TASK"
            )
        ]
        
        # Execute workflow and get results
        results = asyncio.run(workflow.execute_workflow(tasks))
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].content["task_id"], "1")
        self.assertEqual(results[0].content["result"], "processed data")
        self.assertEqual(results[1].content["task_id"], "2")
        self.assertEqual(results[1].content["result"], "report generated")
    
    def test_conditional_router_pattern(self):
        # Test the ConditionalRouter communication pattern
        router_agent = MagicMock()
        router_agent.id = "router"
        agent1 = MagicMock()
        agent1.id = "agent1"
        agent2 = MagicMock()
        agent2.id = "agent2"
        
        router_messaging = MessagingCapability(router_agent, self.broker)
        agent1_messaging = MessagingCapability(agent1, self.broker)
        agent2_messaging = MessagingCapability(agent2, self.broker)
        
        # Create conditional router
        router = ConditionalRouter(router_messaging)
        
        # Add routing rules
        def is_code_message(message):
            return message.content.get("type") == "code"
            
        def is_doc_message(message):
            return message.content.get("type") == "documentation"
        
        router.add_route(is_code_message, agent1_messaging)
        router.add_route(is_doc_message, agent2_messaging)
        
        # Create test messages
        agent1_messages = []
        agent2_messages = []
        
        async def agent1_handler(msg):
            agent1_messages.append(msg)
            
        async def agent2_handler(msg):
            agent2_messages.append(msg)
        
        agent1_messaging.register_handler(agent1_handler)
        agent2_messaging.register_handler(agent2_handler)
        
        # Create and route messages
        code_message = Message(
            sender_id="external",
            content={"type": "code", "data": "function code(){}"},
            message_type="CONTENT"
        )
        
        doc_message = Message(
            sender_id="external",
            content={"type": "documentation", "data": "API documentation"},
            message_type="CONTENT"
        )
        
        unknown_message = Message(
            sender_id="external",
            content={"type": "unknown", "data": "some data"},
            message_type="CONTENT"
        )
        
        asyncio.run(router.route_message(code_message))
        asyncio.run(router.route_message(doc_message))
        asyncio.run(router.route_message(unknown_message))
        
        # Verify routing
        self.assertEqual(len(agent1_messages), 1)
        self.assertEqual(len(agent2_messages), 1)
        
        self.assertEqual(agent1_messages[0].content["type"], "code")
        self.assertEqual(agent2_messages[0].content["type"], "documentation")
    
    def test_agent_pool_pattern(self):
        # Test the AgentPool communication pattern
        pool_manager = MagicMock()
        pool_manager.id = "pool_manager"
        
        worker1 = MagicMock()
        worker1.id = "worker1"
        worker2 = MagicMock()
        worker2.id = "worker2"
        worker3 = MagicMock()
        worker3.id = "worker3"
        
        manager_messaging = MessagingCapability(pool_manager, self.broker)
        worker1_messaging = MessagingCapability(worker1, self.broker)
        worker2_messaging = MessagingCapability(worker2, self.broker)
        worker3_messaging = MessagingCapability(worker3, self.broker)
        
        # Create agent pool
        pool = AgentPool(manager_messaging, [worker1_messaging, worker2_messaging, worker3_messaging])
        
        # Set up task handling
        async def process_task(agent_messaging, task):
            agent_id = agent_messaging.agent.id
            return Message(
                sender_id=agent_id,
                receiver_id=task.sender_id,
                content={
                    "task_id": task.content["task_id"],
                    "result": f"Processed by {agent_id}",
                    "status": "completed"
                },
                message_type="TASK_RESULT",
                correlation_id=task.id
            )
        
        # Register the workers as available
        for worker_messaging in [worker1_messaging, worker2_messaging, worker3_messaging]:
            pool.register_worker(worker_messaging, process_task)
        
        # Create tasks
        tasks = [
            Message(
                sender_id=pool_manager.id,
                content={"task_id": f"{i}", "data": f"task{i}"},
                message_type="TASK"
            )
            for i in range(5)  # Create 5 tasks
        ]
        
        # Process tasks through the pool
        results = asyncio.run(pool.process_tasks(tasks))
        
        # Verify results
        self.assertEqual(len(results), 5)
        
        # Each task should be processed by one of the workers
        worker_ids = {worker1.id, worker2.id, worker3.id}
        result_agents = {result.content["result"].split()[-1] for result in results}
        
        # Every processor should be one of our workers
        self.assertTrue(result_agents.issubset(worker_ids))
        
        # With 5 tasks and 3 workers, at least 2 workers should have been used
        self.assertTrue(len(result_agents) >= 2)


if __name__ == "__main__":
    unittest.main()