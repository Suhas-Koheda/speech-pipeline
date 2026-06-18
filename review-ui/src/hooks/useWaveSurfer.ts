import React, { useEffect, useRef, useCallback, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';

interface UseWaveSurferOptions {
  audioPath: string;
  segmentIdentifier?: string;
  initialRate?: number;   // apply this rate as soon as audio is ready
  autoPlay?: boolean;     // start playing immediately on ready
  onReady?: (duration: number) => void;
  onFinish?: () => void;
}

export function useWaveSurfer(containerRef: React.RefObject<HTMLDivElement | null>, opts: UseWaveSurferOptions) {
  const wsRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRateState] = useState(opts.initialRate ?? 1.0);
  const [error, setError] = useState<string | null>(null);

  // Keep a ref to opts so the 'ready' callback always sees the latest values
  const optsRef = useRef(opts);
  optsRef.current = opts;

  // Track the currently loaded audio path to avoid redundant loads
  const lastLoadedPathRef = useRef<string | null>(null);

  // Persistent HTMLAudioElement instance to prevent autoplay blocks across loads
  const audioRef = useRef<HTMLAudioElement | null>(null);
  if (!audioRef.current) {
    audioRef.current = new Audio();
  }

  // Initialize WaveSurfer ONCE when container becomes available
  useEffect(() => {
    if (!containerRef.current) return;

    const audio = audioRef.current || new Audio();
    audioRef.current = audio;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      media: audio,
      waveColor: 'rgba(99, 102, 241, 0.4)',
      progressColor: 'rgba(99, 102, 241, 0.9)',
      cursorColor: '#818cf8',
      cursorWidth: 2,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 80,
      normalize: true,
      interact: true,
    });

    wsRef.current = ws;

    ws.on('ready', () => {
      const rate = optsRef.current.initialRate ?? 1.0;
      ws.setPlaybackRate(rate);
      setPlaybackRateState(rate);
      setIsReady(true);
      setDuration(ws.getDuration());
      optsRef.current.onReady?.(ws.getDuration());
    });

    ws.on('audioprocess', (t) => setCurrentTime(t));
    ws.on('play', () => setIsPlaying(true));
    ws.on('pause', () => setIsPlaying(false));
    ws.on('finish', () => {
      setIsPlaying(false);
      optsRef.current.onFinish?.();
    });
    ws.on('error', (err) => {
      setError(typeof err === 'string' ? err : 'Failed to load audio');
      setIsReady(false);
    });

    const handleCanPlayThrough = () => {
      if (optsRef.current.autoPlay) {
        console.log(`Autoplaying segment ${optsRef.current.segmentIdentifier || optsRef.current.audioPath}`);
        audio.play().catch((err) => {
          console.warn('Playback failed:', err);
        });
      }
    };

    audio.addEventListener('canplaythrough', handleCanPlayThrough);

    // Load initial audio path and record it
    audio.pause();
    audio.src = optsRef.current.audioPath;
    audio.load();
    ws.load(optsRef.current.audioPath);
    lastLoadedPathRef.current = optsRef.current.audioPath;

    return () => {
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
      ws.destroy();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef]);

  // Load new audio path when it changes (only if different)
  useEffect(() => {
    const ws = wsRef.current;
    const audio = audioRef.current;
    if (!ws || !audio) return;
    if (opts.audioPath === lastLoadedPathRef.current) {
      return;
    }
    setIsReady(false);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setError(null);

    audio.pause();
    audio.src = opts.audioPath;
    audio.load();

    ws.load(opts.audioPath);
    lastLoadedPathRef.current = opts.audioPath;
  }, [opts.audioPath]);

  const togglePlay = useCallback(() => {
    wsRef.current?.playPause();
  }, []);

  const seekTo = useCallback((fraction: number) => {
    wsRef.current?.seekTo(fraction);
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    wsRef.current?.setPlaybackRate(rate);
    setPlaybackRateState(rate);
  }, []);

  const replay = useCallback(() => {
    wsRef.current?.seekTo(0);
    wsRef.current?.play();
  }, []);

  return {
    isPlaying,
    isReady,
    currentTime,
    duration,
    playbackRate,
    error,
    togglePlay,
    seekTo,
    setPlaybackRate,
    replay,
  };
}
