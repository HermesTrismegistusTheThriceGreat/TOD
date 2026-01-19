# Connect MCP clients to Neon

Learn how to connect MCP clients such as Cursor, Claude Code, VS Code,
ChatGPT, and other tools to your Neon Postgres database.

The **Neon MCP Server** allows you to connect various [**Model Context
Protocol
(MCP)**](https://modelcontextprotocol.org)
compatible AI tools to your Neon Postgres databases. This guide provides
instructions for connecting popular MCP clients to the Neon MCP Server,
enabling natural language interaction with your Neon projects.

This guide covers the setup for the following MCP clients:

- [Cursor](#cursor)
- [Claude Code](#claude-code)
- [VS Code (with GitHub Copilot)](#vs-code-with-github-copilot)
- [ChatGPT](#chatgpt)
- [Claude Desktop](#claude-desktop)
- [Cline (VS Code extension)](#cline-vs-code-extension)
- [Windsurf (Codeium)](#windsurf-codeium)
- [Zed](#zed)

Connect these tools to manage your Neon projects, databases, and schemas
using natural language.

#### Neon MCP Server Security Considerations

The Neon MCP Server grants powerful database management capabilities
through natural language requests. **Always review and authorize actions
requested by the LLM before execution.** Ensure that only authorized
users and applications have access to the Neon MCP Server.

The Neon MCP Server is intended for local development and IDE
integrations only. **We do not recommend using the Neon MCP Server in
production environments.** It can execute powerful operations that may
lead to accidental or unauthorized changes.

**For safer operations**, especially when you need to query production
or sensitive data, consider using [read-only
mode](/docs/ai/neon-mcp-server#read-only-mode). This restricts all
operations to read-only tools and ensures SQL queries run in read-only
transactions, preventing accidental modifications.

For more information, see [MCP security guidance
->](/docs/ai/neon-mcp-server#mcp-security-guidance).

## Prerequisites

- An MCP Client application.
- A [Neon
 account](https://console.neon.tech/signup).
- **Node.js (\>= v18.0.0) and npm:** Download from
 [nodejs.org](https://nodejs.org).

For Quick Setup, the API key is created automatically. For Local setup,
you'll need a Neon API key. See [Neon API Keys
documentation](/docs/manage/api-keys#creating-api-keys).

#### note

Ensure you are using the latest version of your chosen MCP client as MCP
integration may not be available in older versions. If you are using an
older version, update your MCP client to the latest version.

## Setup Options

**Quick Setup:** Cursor, Claude Code, and VS Code support automatic
setup with `npx neonctl@latest init`. This configures API key-based
authentication for streamlined tool access with fewer approval prompts.

**Manual Setup:** All editors support **OAuth** (remote server) or
**Local** (run MCP server locally) setup.

#### note

OAuth authentication connects to your personal Neon account by default.
For organization access, use [API key-based
authentication](/docs/ai/neon-mcp-server#api-key-based-authentication).

OAuth authentication supports two transports: Streamable HTTP
(`https://mcp.neon.tech/mcp`) and SSE (`https://mcp.neon.tech/sse`).
Most clients support Streamable HTTP. Use SSE only if your client
doesn't support Streamable HTTP.

## Cursor

Quick Setup
OAuth
Local

Run the init command:

npx neonctl@latest init

Authenticates via OAuth, creates an API key, and configures Cursor to
connect to Neon's remote MCP server. Then ask your AI assistant
"Get started with Neon".

For more, see [Get started with Cursor and Neon Postgres MCP
Server](/guides/cursor-mcp-neon).

## Claude Code

Quick Setup
OAuth
Local

Run the init command:

npx neonctl@latest init

Authenticates via OAuth, creates an API key, and configures Claude
Code to connect to Neon's remote MCP server. Then ask your AI assistant
"Get started with Neon".

For more, see [Get started with Claude Code and Neon Postgres MCP
Server](/guides/claude-code-mcp-neon).

## VS Code (with GitHub Copilot)

#### note

To use MCP servers with VS Code, you need [GitHub
Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) and [GitHub Copilot
Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) extensions installed

Quick Setup
OAuth
Local

Run the init command:

npx neonctl@latest init

Authenticates via OAuth, creates an API key, and configures VS Code
to connect to Neon's remote MCP server. Then ask your AI assistant
"Get started with Neon".

For a detailed guide including an Azure Function REST API example, see
[Using Neon MCP Server with GitHub Copilot in VS
Code](/guides/neon-mcp-server-github-copilot-vs-code).

## ChatGPT

Connect ChatGPT to Neon using custom MCP connectors. Enable Developer
mode, add the Neon connector, then enable it per chat.

[![ChatGPT with Neon MCP
Server]([image])]

1. **Add MCP server to ChatGPT**

 In your ChatGPT account settings, go to **Settings** ->
 **Connectors** -> **Advanced Settings** and enable **Developer
 mode**.

 Still on the Connectors tab, you can then **create** a Neon
 connection from the **Browse connectors** section. Use the following
 URL:

 https://mcp.neon.tech/mcp

 Make sure you choose **OAuth** for authentication and check \"I
 trust this application\", then complete the authorization flow when
 prompted.

 [![ChatGPT connector
 configuration]([image])]

 [![ChatGPT with Neon MCP tools
 enabled]([image])]

2. **Enable Neon per chat**

 In each chat where you want to use Neon, click the **+** button and
 enable Developer Mode for that chat. Under **Add sources**, you can
 then enable the Neon connector you just created.

 Once connected, you can use natural language to manage your Neon
 databases directly in ChatGPT.

## Claude Desktop

OAuth
Local

Open Claude desktop and navigate to
Settings.
Under the Developer tab, click Edit
Config (On Windows, it's under File - Settings -
Developer - Edit Config) to open the configuration file
(claude_desktop_config.json).
Add the "Neon" server entry within the mcpServers
object:

 }
}

Save the configuration file and restart Claude
Desktop.
An OAuth window will open in your browser. Follow the prompts to
authorize Claude Desktop to access your Neon account.

For more, see [Get started with Neon MCP server with Claude
Desktop](/guides/neon-mcp-server).

## Cline (VS Code Extension)

OAuth
Local

Open Cline in VS Code (Sidebar - Cline icon).
Click MCP Servers Icon -
Installed - Configure MCP Servers
to open the configuration file.
Add the "Neon" server entry within the mcpServers
object:

 }
}

Save the file. Cline should reload the configuration
automatically.
An OAuth window will open in your browser. Follow the prompts to
authorize Cline to access your Neon account.

For more, see [Get started with Cline and Neon Postgres MCP
Server](/guides/cline-mcp-neon).

## Windsurf (Codeium)

OAuth
Local

Open Windsurf and navigate to the Cascade assistant
sidebar.
Click the hammer (MCP) icon, then Configure
which opens up the "Manage MCPs" configuration file.
Click on "View raw config" to open the raw configuration file in
Windsurf.
Add the "Neon" server entry within the mcpServers
object:

 }
}

Save the file.
Click the Refresh button in the Cascade sidebar
next to "available MCP servers".
An OAuth window will open in your browser. Follow the prompts to
authorize Windsurf to access your Neon account.

For more, see [Get started with Windsurf and Neon Postgres MCP
Server](/guides/windsurf-mcp-neon).

## Zed

#### note

MCP support in Zed is currently in **preview**. Ensure you're using the
Preview version of Zed to add MCP servers (called **Context Servers** in
Zed). Download the preview version from
[zed.dev/releases/preview](https://zed.dev/releases/preview).

OAuth
Local

Open the Zed Preview application.
Click the Assistant (✨) icon in the bottom right
corner.
Click Settings in the top right panel of the
Assistant.
In the Context Servers section, click +
Add Context Server.
Configure the Neon Server:

Enter Neon in the Name field.
In the Command field, enter:

npx -y mcp-remote https://mcp.neon.tech/mcp

Click Add Server.

An OAuth window will open in your browser. Follow the prompts to
authorize Zed to access your Neon account.
Check the Context Servers section in Zed settings to ensure the
connection is successful. "Neon" should be listed.

For more details, including workflow examples and troubleshooting, see
[Get started with Zed and Neon Postgres MCP
Server](/guides/zed-mcp-neon).

## Other MCP clients

Adapt the instructions above for other clients:

- **OAuth authentication:** Add the following JSON configuration within
 the `mcpServers` section of your client's `MCP` configuration file:

 neon:

 > MCP supports two remote server transports: the deprecated
 > Server-Sent Events (SSE) and the newer, recommended Streamable HTTP.
 > If your LLM client doesn't support Streamable HTTP yet, you can
 > switch the endpoint from `https://mcp.neon.tech/mcp` to
 > `https://mcp.neon.tech/sse` to use SSE instead.

 Then follow the OAuth flow on first connection.

- **Local setup:**

 Add the following JSON configuration within the `mcpServers` section
 of your client's `MCP` configuration file, replacing
 `` with your Neon API key:

 MacOS/Linux
 Windows
 Windows (WSL)

 For MacOS and Linux, add the following JSON
 configuration within the mcpServers section of your
 client's mcp_config file, replacing
 YOUR_NEON_API_KEY with your Neon API key:

 neon:

 #### note

 After successful configuration, you should see the Neon MCP Server
 listed as active in your MCP client's settings or tool list. You can
 enter \"List my Neon projects\" in the MCP client to see your Neon
 projects and verify the connection.

## Troubleshooting

### Configuration Issues

If your client does not use `JSON` for configuration of MCP servers
(such as older versions of Cursor), you can use the following command
when prompted:

# For OAuth (remote server)
npx -y mcp-remote https://mcp.neon.tech/mcp

# For Local setup
npx -y @neondatabase/mcp-server-neon start YOUR_NEON_API_KEY

### OAuth Authentication Errors

When using the remote MCP server with OAuth authentication, you might
encounter the following error:

This typically occurs when there are issues with cached OAuth
credentials. To resolve this:

1. Remove the MCP authentication cache directory:

 rm -rf ~/.mcp-auth

2. Restart your MCP client application
3. The OAuth flow will start fresh, allowing you to properly
 authenticate

This error is most common when using OAuth authentication and can occur
after OAuth configuration changes or when cached credentials become
invalid.

## Next steps

Once connected, you can start interacting with your Neon Postgres
databases using natural language commands within your chosen MCP client.
Explore the [Supported Actions
(Tools)](/docs/ai/neon-mcp-server#supported-actions-tools) of the Neon
MCP Server to understand the available functionalities.

## Resources

- [MCP
 Protocol](https://modelcontextprotocol.org)
- [Neon API
 Reference](https://api-docs.neon.tech/reference/getting-started-with-neon-api)
- [Neon API Keys](/docs/manage/api-keys#creating-api-keys)
- [Neon MCP server
 GitHub](https://github.com/neondatabase/mcp-server-neon)
- [VS Code MCP Server
 Documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

## Need help?

Join our [Discord
Server](https://discord.gg/92vNTzKDGp) to ask
questions or see what others are doing with Neon. For paid plan support
options, see [Support](/docs/introduction/support).

[Previous][Overview](/docs/ai/neon-mcp-server)[Next][AI
rules](/docs/ai/ai-rules)

Last updated on December 17, 2025

::::: relative

[Was this page helpful?]

Yes

No

[Thank you for your feedback!]

### On this page

- [Prerequisites](#prerequisites)
- [Setup Options](#setup-options)
- [Cursor](#cursor)
- [Claude Code](#claude-code)
- [VS Code (with GitHub Copilot)](#vs-code-with-github-copilot)
- [ChatGPT](#chatgpt)
- [Claude Desktop](#claude-desktop)
- [Cline (VS Code Extension)](#cline-vs-code-extension)
- [Windsurf (Codeium)](#windsurf-codeium)
- [Zed](#zed)
- [Other MCP clients](#other-mcp-clients)
- [Troubleshooting](#troubleshooting)
- [Next steps](#next-steps)
- [Resources](#resources)
- [Need help?](#need-help)

[Copy
page as markdown]

[Edit
this page on GitHub](https://github.com/neondatabase/website/tree/main/content/docs/ai/connect-mcp-clients-to-neon.md)[Open
in ChatGPT](https://chatgpt.com/?hints=search&q=Read+https://raw.githubusercontent.com/neondatabase/website/refs/heads/main/content/docs/ai/connect-mcp-clients-to-neon.md)

[Neon
Docs]
