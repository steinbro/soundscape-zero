#!/usr/bin/env python3
import json

import aiopg
import psycopg2
from psycopg2.extras import NamedTupleCursor
import sentry_sdk

from overpass import ZOOM_DEFAULT


tile_query = """
    SELECT * from soundscape_tile(%(zoom)s, %(tile_x)s, %(tile_y)s)
"""


class PostgisClient:
    """A drop-in replacement for OverpassClient that uses a PostGIS server.
    The server is assumed to already be populated, including having the
    soundscape_tile function installed.
    """
    def __init__(self, server, user_agent, cache_dir, cache_days, cache_size):
        # all the other args are only used by the OverpassClient
        self.server = server

    @sentry_sdk.trace
    async def query(self, x, y):
        async with aiopg.connect(self.server) as conn:
            async with conn.cursor(cursor_factory=NamedTupleCursor) as cursor:
                response = await self._gentile_async(cursor, x, y)
                return response

    # based on https://github.com/microsoft/soundscape/blob/main/svcs/data/gentiles.py
    async def _gentile_async(self, cursor, x, y, zoom=ZOOM_DEFAULT):
        try:
            await cursor.execute(tile_query, {'zoom': int(zoom), 'tile_x': x, 'tile_y': y})
            value = await cursor.fetchall()
            return {
                'type': 'FeatureCollection',
                'features': list(map(lambda x: x._asdict(), value))
            }
        except psycopg2.Error as e:
            print(e)
            raise
