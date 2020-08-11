import base64
from datetime import datetime
import traceback
import aiomysql
from .BasePlugin import BasePlugin
import discord
from discord.ext import commands
from cogs.utils.paginator import Pages
from bot_mp import ClusterBot as Bot


class encodeType:

    class encode:
        pass

    class decode:
        pass


def encoder_system(_type, _to_handle):
    if _type is encodeType.decode:
        return base64.b64decode(_to_handle).decode('utf-8')
    elif _type is encodeType.encode:
        return base64.b64encode(bytes(_to_handle, "utf-8")).decode("utf-8")
    else:
        return


class Todo(BasePlugin):

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx: commands.Context):
        embed = discord.Embed(color=self.bmo.EMBED_COLOR, title="TODO help")
        embed.add_field(name="Help", value="Shows this message", inline=False)
        embed.add_field(name="List/Show",
                        value="Lists all of your items inside your todo list",
                        inline=False)
        embed.add_field(name="Create/Add",
                        value="Creates an item from your todo list",
                        inline=False)
        embed.add_field(name="Delete/Del/Rm",
                        value="Deletes an item from your todo list",
                        inline=False)
        await ctx.send(embed=embed)

    @todo.command(aliases=["show"])
    async def list(self, ctx: commands.Context):
        todos = []
        async with self.bmo.SQL_POOL.acquire() as conn:
            async with conn.cursor() as cur:
                cur = cur  # type: aiomysql.Cursor
                await cur.execute(
                    'SELECT text FROM todo WHERE user_id = {} ORDER BY time'.
                    format(ctx.author.id))
                for num, todo, in enumerate(await cur.fetchall()):
                    todos.append(
                        f"`[{num + 1}]` {encoder_system(encodeType.decode, todo[0])}\n"
                    )

        if not len(todos):
            return await ctx.send(f"⚠| You don't have any todos")
        paginator = Pages(ctx,
                          entries=todos,
                          per_page=5,
                          show_entry_count=False,
                          title="Your todo list:")
        try:
            await paginator.paginate()
        except discord.HTTPException:
            paginator = Pages(ctx,
                              title=f"Your todo list:",
                              entries=todos,
                              show_entry_count=False,
                              per_page=1)
            await paginator.paginate()

        await paginator.paginate()

    @commands.cooldown(1, 30, commands.BucketType.user)
    @todo.command(aliases=["add"])
    async def create(self, ctx: commands.Context, *, text: str):
        """Adds a item to your todolist"""
        user_todos = await self.bmo.execute_sql(
            query="SELECT * FROM todo WHERE user_id = {}".format(ctx.author.id),
            fetch_all=True)
        if len(user_todos) >= 20 and await self.bmo.is_donator(ctx.author.id
                                                              ) < 3:
            return await ctx.send(
                "⚠| having more than 20 items on the todo list is for donator tier 3+"
            )
        elif len(text) > 500:
            return await ctx.send(
                f"you can have a todo up to 500 chars long! ({len(text)}/500)")
        encoded_data = encoder_system(encodeType.encode, text)
        ret = await self.bmo.execute_sql(
            query="INSERT INTO todo(user_id, time, text) VALUES ({}, '{}', '{}')"
            .format(ctx.author.id, datetime.utcnow(), encoded_data),
            commit=True)
        if not ret:
            await ctx.send(
                "✅| Added {} to the todo list and should appear in around 1 minute globally"
                .format(text),
                allowed_mentions=discord.AllowedMentions(everyone=False,
                                                         users=False,
                                                         roles=False))
        else:
            await ctx.send(
                "⚠| failed to add {} to todo list, {}".format(text, ret),
                allowed_mentions=discord.AllowedMentions(everyone=False,
                                                         users=False,
                                                         roles=False))

    @commands.cooldown(1, 30, commands.BucketType.user)
    @todo.command(aliases=["del", "rm"])
    async def delete(self, ctx: commands.Context, *, todo_id: str):
        """deletes an item from your todolist by id"""
        todos = await self.bmo.execute_sql(
            query="SELECT * FROM todo WHERE user_id = {} ORDER BY `time`".
            format(ctx.author.id),
            fetch_all=True)
        if not todos:
            return await ctx.send("❌| you don't have any todo items")
        todos = {f'{index + 1}': todo for index, todo in enumerate(todos)}
        todos_to_remove = []

        todo_ids = todo_id

        todo_ids = todo_ids.split(' ')
        for todo_id in todo_ids:

            if not todo_id.isdigit():
                return await ctx.send(f'❌| Invalid TODO item ID')
            if todo_id not in todos.keys():
                return await ctx.send(f'❌| Incorrect TODO ID')
            if todo_id in todos_to_remove:
                return await ctx.send(
                    f'❌| You tried to delete {todo_id} multiple times.')
            todos_to_remove.append(todo_id)
        query = 'DELETE FROM todo WHERE user_id = %s and time = %s'
        entries = [(todos[todo_id][0], todos[todo_id][1])
                   for todo_id in todos_to_remove]
        async with self.bmo.SQL_POOL.acquire() as conn:
            conn = conn  # type: aiomysql.Connection
            async with conn.cursor() as cur:
                cur = cur  # type: aiomysql.Cursor
                await cur.executemany(query, entries)
                await cur.close()
            await conn.commit()
            conn.close()

        return await ctx.send(
            f"✅ Removed `{len(todo_ids)}` todo items from your todo list")


def setup(bot):
    bot.add_cog(Todo(bot))
