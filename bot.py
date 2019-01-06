#pylint: disable-msg=too-many-arguments
#pylint: disable-msg=R0913
import discord
import asyncio
import copy
client = discord.Client()
idiot_proof = True
conversations = []
tasks = []
role_backup = {}

emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣", "🔟", "📗", "📘", "📙", "📓", "📒", "🔋", "🔮", "💣",
    "🏹", "🗡", "⛏", "🎵", "🎲", "🏀", "👑", "🎁", "🚗", "🌍", "🚩"]


def idiot_proof_perms(permissions):
    return (permissions.administrator or permissions.manage_channels or permissions.manage_server or permissions.ban_members or permissions.kick_members or permissions.mention_everyone)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    if client.user.mentioned_in(message) and message.author.id != client.user.id and not message.channel.is_private:
        await run_command(message, message.channel, message.author)
                
async def run_command(message, channel, user):
    print(message.author.name + "[" + message.author.id + "]" + " : " + message.content)
    if message.author.server_permissions.administrator and "help" in message.content:
        await client.send_message(message.author, "I currently support the following commands:\n\n**rolelist** - setup a list of roles that users can react to\n**private** - allows you to execute commands in the channel by pming them to me instead of saying them out loud\n**backup** - backs up the server, preserving channels, permissions, and roles\n**possess** - allows you to speak as me by pming me what you want me to say\n\n\nTo execute any of these commands, just ping me.")
    elif message.author.server_permissions.administrator and "private" in message.content:
        conversations.append(Conversation(message.user, message, "Opened private conversation"))
        await client.send_message(message.author, "Opened a private channel. Commands will be relayed to " + message.server.name + "** in channel #" + message.channel.name)
    elif message.author.server_permissions.administrator and "backup" in message.content:
        await backup_server(message.server)
    elif message.author.server_permissions.administrator and "possess" in message.content:
        await client.send_message(message.author, "You have now taken control of me. Any messages you send in this private chat will be relayed to server **" + message.server.name + "** in channel #" + message.channel.name + "\nTo terminate this connection, please react to the above message")
        asyncio.ensure_future(possess_loop(message.author, message.channel))
    elif message.author.server_permissions.administrator and "rolelist" == message.content.lower():
        total_roles = message.server.roles
        emoji_iterator = iter(emojis)
        react_message = ReactionRoleMessage()
        emoji_list = []
        for role in total_roles:
            if (not role.is_everyone and (not idiot_proof or not idiot_proof_perms(role.permissions))):
                reaction = next(emoji_iterator)
                emoji_list.append(reaction)
                react_message.addLine(reaction, role)
                #print( reaction + ":" + role.name)
            else:
                total_roles.remove(role)
        react_message.message = await client.send_message(message.channel, react_message.getText())
        example = react_message.getExample()
        stray_messages = []
        stray_messages.append(await client.send_message(message.channel, message.author.mention + " Next: Are there any roles that shouldn't be on this list? Remove them now by reacting to the above message. For example, to remove role **" + example[0] + "** from the list, react with " + example[1]))
        stray_messages.append(await client.send_message(message.channel, "When you're finished, just say 'done'"))
        conversation = Conversation(message.author, react_message.message, "Deleting roles from list")
        conversations.append(conversation)
        for emote in emoji_list:
            await client.add_reaction(react_message.message, emote)
        try:
            remover = asyncio.ensure_future(format_rolelist_loop(react_message))
            stray_messages.append(await client.wait_for_message(timeout=60 * 5, author=message.author, channel=message.channel, content="done"))
        except asyncio.TimeoutError:
            return
        finally:
            remover.cancel()
            conversations.remove(conversation)
            await client.delete_messages(iter(stray_messages))
            react_message.active = True
            asyncio.ensure_future(give_role_loop(react_message))

async def possess_loop(user, channel):
    while(True):
        try:
            message = await client.wait_for_message(timeout=60 * 5, author=user)
        except asyncio.TimeoutError:
            return
        if (message.channel.is_private):
            await client.send_message(channel, message.content)

async def give_role_loop(msg):
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        role = msg.role_dict[res.reaction.emoji][1]
        if role.permissions.administrator:
            print("ALERT! " + res.user.name + " tried to get role " + role.name + " which has administrative privileges!")
        else:
            await client.add_roles(res.user, role)

async def remove_role_loop(msg):
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        role = msg.role_dict[res.reaction.emoji][1]
        if role.permissions.administrator:
            print("ALERT! " + res.user.name + " tried to remove role " + role.name + " which has administrative privileges!")
        else:
            await client.remove_roles(res.user, role)

async def format_rolelist_loop(msg):
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        reaction = res.reaction
        user = res.user
        conversation = getConversation(conversations, reaction.message, user)
        react_message = msg
        if conversation is not None and conversation.description == "Deleting roles from list":
            react_message.removeLine(reaction.emoji)
            await client.edit_message(reaction.message, new_content=react_message.getText())
            await client.remove_reaction(reaction.message, reaction.emoji, client.user)
            await client.remove_reaction(reaction.message, reaction.emoji, user)
        else:
            return

async def backup_server(server):
    user_roles = {}
    role_backup[server.id] = user_roles
    await client.request_offline_members(server)
    count = 0
    for member in server.members:
        user_roles[member.id] = member.roles
        print("Giving " + member.name + " the roles [" + member.roles + "]")
    print(count + "users backed up.")

def getConversation(conversations, message, user):
    for conversation in conversations:
        if conversation.user.id == user.id and conversation.last_message.id == message.id and message.channel.id == conversation.last_message.channel.id:
            return conversation
    return None

class Conversation:
    def __init__(self, user, last_message, description):
        self.user = user
        self.last_message = last_message
        self.description = description
    def __eq__(self, other):
        return (self.user == other.user and self.last_message == other.last_message and self.description == other.description)

class ReactionRoleMessage:
    def __init__(self):
        self.message = None
        self.role_dict = {}
        self.active = False
    def addLine(self, reaction, role):
        value = ["React with " + \
            reaction + " for role " + role.name + "\n", role]
        self.role_dict[reaction] = value

    def removeLine(self, reaction):
        del self.role_dict[reaction]

    def getText(self):
        result = ""
        for line in list(self.role_dict.values()):
            result += line[0]
        return result
        
    def getExample(self):
        return [list(self.role_dict.values())[0][1].name, list(self.role_dict.keys())[0]]


client.run('NTI3OTA2OTc0MTkzNTQ5MzE0.DwmAqg.x-GYbJSWrQiNfYEZmBMEFkmVoFs')
