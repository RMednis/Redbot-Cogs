import discord
import lavalink
import logging

from ttsengine import file_manager

log = logging.getLogger("red.mednis-cogs.poitranslator.audio_manager")


async def skip_tts(self):
    log.info("Skipping TTS track.")

    if self.llplayer is not None:
        player = self.llplayer
        current_track = player.current

        if current_track is not None:
            if current_track.track_identifier in self.tts_queue:
                track = player.current
                await player.skip()
                await delete_file_and_remove(self, track)
            else:
                raise RuntimeError("No TTS message is playing currently!")
        else:
            raise RuntimeError("No TTS message is playing currently!")
    else:
        raise RuntimeError("Could not connect to voice server or `(lavalink)`!")


async def reconnect_ll(self, vc: discord.VoiceChannel):
    try:
        self.llplayer = await lavalink.connect(vc, self_deaf=True)
    except lavalink.errors.NodeNotFound:
        raise RuntimeError("Lavalink/Discord is not yet ready!")


async def play_audio(self, vc: discord.VoiceChannel, file_path: str, volume: int, track_name: str = "TTS"):

    # If we don't have a lavalink reference cached.
    if self.llplayer is None:
        await reconnect_ll(self, vc)

    player = self.llplayer

    try:
        # Try and use our existing LavaLink client
        response = (await player.load_tracks(file_path))

    except RuntimeError and lavalink.errors.PlayerException:
        try:
            # LavaLink is not connected
            await reconnect_ll(self, vc)

            # Try and fix it
            player = self.llplayer
            response = (await player.load_tracks(file_path))
        except RuntimeError and lavalink.errors.PlayerException as err:
            log.error("Failed to connect while trying to play TTS :(")
            log.error(err)

    # Response can theoretically give us multiple tracks... we only need one.
    if len(response.tracks) > 0:
        track = response.tracks[0]
    else:
        log.error(f"Could not load track {file_path}")
        return

    # log.info(f"Current Volume: {player.volume}")

    # Set the track title to something sane, so we don't just leak the entire directory structure of whatever host the
    # bot is running on
    track.title = track_name

    # If the player is not playing anything, play the track.
    if player.current is None:
        log.info("There was no track playing, playing the tts track.")

        # Append the track to the audio queue.
        player.queue.append(track)

        # Append the track to the TTS queue.
        self.tts_queue.append(track.track_identifier)

        # Set the player volume to our global volume
        await player.set_volume(volume)

        # Play the track.
        await player.play()
        return

    # Check if we are playing a TTS message already
    if player.current.track_identifier in self.tts_queue:
        # if we are already playing tts, add it to the audio queue
        player.queue.insert(len(self.tts_queue) - 1, track)
        # Then append it to the TTS queue
        self.tts_queue.append(track.track_identifier)
        return

    else:
        # If the player is playing something else, save the current track and position.
        last_non_tts_track = (player.current, player.position, player.paused, player.volume)

        self.tts_queue.append(track.track_identifier)  # Append the track to the TTS queue.

        player.queue.insert(0, track)  # Insert the new track into the top of the queue.

        # Add the saved track after the new track, at the same position it was stopped at.
        player.queue.insert(1, last_non_tts_track[0])
        self.last_non_tts_track = last_non_tts_track

        # Skip the current track.
        await player.skip()

        # Set the player volume to the TTS global volume
        await player.set_volume(volume)


async def delete_file_and_remove(self, track):
    log.info("Deleting tts track and removing it from the queue.")
    log.info(self.tts_queue)

    # If the track ended, delete the audio file.
    await file_manager.delete_audio(track.uri)

    # Remove the track from the queue.
    self.tts_queue.remove(track.track_identifier)
