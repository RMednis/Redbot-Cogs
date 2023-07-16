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
                player.skip()
                await delete_file_and_remove(current_track.track_identifier)
            else:
                raise RuntimeError("No TTS message is playing currently!")
        else:
            raise RuntimeError("No TTS message is playing currently!")
    else:
        raise RuntimeError("Could not connect to voice server or `(lavalink)`!")


async def play_audio(self, vc: discord.VoiceChannel, file_path):
    if self.llplayer is None:
        self.llplayer = await lavalink.connect(vc, self_deaf=True)

    player = self.llplayer
    log.info(f"Tts queue length: {len(self.tts_queue)}")

    try:
        response = (await player.load_tracks(file_path))
    except RuntimeError:
        self.llplayer = await lavalink.connect(vc, self_deaf=True)
        player = self.llplayer
        response = (await player.load_tracks(file_path))

    if len(response.tracks) > 0:
        track = response.tracks[0]
    else:
        log.error(f"Could not load track {file_path}")
        return

    # If the player is not playing anything, play the track.
    if player.current is None:
        log.info("There was no track playing, playing the tts track.")

        # Append the track to the audio queue.
        player.queue.append(track)

        # Append the track to the TTS queue.
        self.tts_queue.append(track.track_identifier)

        # Play the track.
        await player.play()
        return

    log.info(player.current.track_identifier)
    if player.current.track_identifier in self.tts_queue:
        log.info(
            f"There is a TTS track playing, adding the new tts track to the queue at position  {len(self.tts_queue)}")

        # if we are already playing tts, add it to the audio queue
        player.queue.insert(len(self.tts_queue) - 1, track)
        # Then append it to the TTS queue
        self.tts_queue.append(track.track_identifier)
        return

    else:
        log.info("There is a non-tts track playing, stopping it and playing the tts track.")

        # If the player is playing something else, save the current track and position.
        last_non_tts_track = (player.current, player.position)

        self.tts_queue.append(track.track_identifier)  # Append the track to the TTS queue.

        player.queue.insert(0, track)  # Insert the new track into the top of the queue.

        # Add the saved track after the new track, at the same position it was stopped at.
        player.queue.insert(1, last_non_tts_track[0])
        self.last_non_tts_track = last_non_tts_track

        # Skip the current track.
        await player.skip()


async def delete_file_and_remove(self):
    log.info("Deleting tts track and removing it from the queue.")
    log.info(self.tts_queue)

    # If the track ended, delete the audio file.
    await file_manager.delete_audio(self.tts_queue[0].uri)
    # Remove the track from the queue.
    await self.tts_queue.pop(0)
