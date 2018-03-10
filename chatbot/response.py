from microsoftbotframework import ReplyToActivity
from luis_sdk import LUISClient

import goals
import actions


class Bot(object):
    def __init__(self):
        self.goal_stack = []
        self.action_stack = []
        self.prompting = False
        self.current_action = None
        self.variables = {}
        self.decision = None
	    # Set this if helpful
        self.file_path = ''
        self.goal_intents = {
        }

        self.action_intents = {
            "Greeting": actions.Greet(),
            "Help": actions.ProvideAssisstance()
        }

    def respond(self, message):
        """Response Logic
        
        This function implaments a goal-based response logic.  It is of fairly
        general design and should work for many situations.
        
        The logic maintains two stacks for goals and actions.  User intents are
        the primary way goals are added to the stack. Each goal corresponds
        to a set of a few actions.

        We will use LUIS to match intents with goals to add and entities to
        pull out the desired values when prompting the user.
        """
        if message["type"] == "message":
            # DEBUG logging of cureent goal/action stacks
            print(f"Goal Stack: {self.goal_stack}")
            print(f"Action Stack: {self.action_stack}")
            if self.prompting:
                print("Prompting is true, saving next message")
                # This is the highest priority channel, and is set
                # by certain actions which are trying to collect input
                self.current_action.process_response(self, message)
                # Then revert prompting to false
                self.prompting = False
                # Since the message has been used, we'll null the 
                # text.  This reduces the noise sent to LUIS.
                message["text"] = ""
                # Finally, since it is likely that we want to do something
                # with the input, we'll trigger another pass through the
                # response logic
                self.respond(message)

            elif self.action_stack != []:
                print("Actions on stack, executing...")
                # If there are any actions on the stack, then we want
                # to resolve those before adding any new goals. 
                while (self.action_stack != []) and (not self.prompting):
                    # We typically want to execute several actions in series
                    # without user input inbetween.  This logic processes
                    # actions until we encounter a prompt.  The prompt is
                    # then resolved before clearing the rest of the actions.
                    self.current_action = self.action_stack.pop()
                    print("The state of the current action stack is" +
                          f"{self.action_stack}")
                    # Process input in preprogrammed way
                    self.current_action.act(self, message)
                    # Set prompting state if current action needs it
                    self.prompting = self.current_action.prompt

            elif self.goal_stack != []:
                print("Goal on stack, exectuing...")
                # If we multiple goals loaded on the stack, this step will
                # pop the next.
                self.current_goal = self.goal_stack.pop()
                print(f"The current goal is {self.current_goal.name}")
                # Extract the actions from that goal and reverse the list
                queue_actions = self.current_goal.actions
                queue_actions.reverse()
                # Add the actions to the stack
                self.action_stack += queue_actions
                # Since we've just added actions, we'll want to get them
                # started without user input
                self.respond(message)

            else:
                # With no goal/action to process it is safe to assume that
                # we are trying to determine a new goal.
                print("No goals on stack, processing intent...")
                # Send message to LUIS to process intent
                res = self.make_request(message['text'])
                # Grab top scoring intent
                top_intent = res.get_top_intent().get_name()
                print(f"Intent is {top_intent}")

                if top_intent in self.goal_intents.keys():
                    # Intents in our dictionary have specified goals attached
                    # so we load that to the stack
                    self.goal_stack.append(self.goal_intents[top_intent])
                    # We'll now want to process the goal without user input
                    self.respond(message)

                elif top_intent in self.action_intents.keys():
                    self.action_intents[top_intent].act(self, message)

                else:
                    ReplyToActivity(fill=message,
                                    text="Sorry, but I either don't understand\
                                            what you want or I don't support  \
                                            that action yet").send()

    def make_request(self, message):
        """Send message from user to LUIS for intent analysis"""
        # TODO: Store this data safely
        # Hard coded LUIS APP ID and Authoring Key
        APPID = ''
        APPKEY = ''
        try:
            CLIENT = LUISClient(APPID, APPKEY, True)
            res = CLIENT.predict(message)
            while res.get_dialog() is not None and not res.get_dialog()\
                                                          .is_finished():
                TEXT = input('%s\n' % res.get_dialog().get_prompt())
                res = CLIENT.reply(TEXT, res)
            return res
        except Exception as exc:
            print(exc)
