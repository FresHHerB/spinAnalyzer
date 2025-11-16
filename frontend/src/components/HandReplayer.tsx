import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, SkipBack, SkipForward, Play, Pause } from 'lucide-react';
import type { DecisionPoint } from '@/types';

interface HandReplayerProps {
  hand: DecisionPoint;
}

interface Street {
  name: string;
  actions: string[];
  pot: number;
  board: string;
}

export default function HandReplayer({ hand }: HandReplayerProps) {
  const [currentActionIndex, setCurrentActionIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Parse hand into streets and actions
  const streets = useMemo(() => {
    const parsed: Street[] = [];

    // Preflop
    if (hand.preflop_actions) {
      parsed.push({
        name: 'Preflop',
        actions: hand.preflop_actions.split(',').map(a => a.trim()),
        pot: hand.pot_bb,
        board: ''
      });
    }

    // Flop
    if (hand.flop_actions && hand.flop_board) {
      parsed.push({
        name: 'Flop',
        actions: hand.flop_actions.split(',').map(a => a.trim()),
        pot: hand.pot_bb,
        board: hand.flop_board
      });
    }

    // Turn
    if (hand.turn_actions && hand.turn_board) {
      parsed.push({
        name: 'Turn',
        actions: hand.turn_actions.split(',').map(a => a.trim()),
        pot: hand.pot_bb,
        board: hand.turn_board
      });
    }

    // River
    if (hand.river_actions && hand.river_board) {
      parsed.push({
        name: 'River',
        actions: hand.river_actions.split(',').map(a => a.trim()),
        pot: hand.pot_bb,
        board: hand.river_board
      });
    }

    return parsed;
  }, [hand]);

  const totalActions = streets.reduce((sum, s) => sum + s.actions.length, 0);
  const currentStreet = useMemo(() => {
    let actionCount = 0;
    for (const street of streets) {
      if (currentActionIndex < actionCount + street.actions.length) {
        return street;
      }
      actionCount += street.actions.length;
    }
    return streets[streets.length - 1] || null;
  }, [currentActionIndex, streets]);

  const handleNext = () => {
    if (currentActionIndex < totalActions - 1) {
      setCurrentActionIndex(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentActionIndex > 0) {
      setCurrentActionIndex(prev => prev - 1);
    }
  };

  const handleFirst = () => setCurrentActionIndex(0);
  const handleLast = () => setCurrentActionIndex(Math.max(0, totalActions - 1));

  const togglePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  // Auto-play functionality
  useState(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentActionIndex(prev => {
        if (prev >= totalActions - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(interval);
  });

  // Parse card notation (e.g., "As" = Ace of Spades)
  const renderCard = (card: string) => {
    if (!card || card.length !== 2) return null;

    const rank = card[0];
    const suit = card[1];

    const suitSymbols: Record<string, string> = {
      's': '♠',
      'h': '♥',
      'd': '♦',
      'c': '♣'
    };

    const suitColors: Record<string, string> = {
      's': 'text-gray-900 dark:text-gray-100',
      'h': 'text-red-600 dark:text-red-400',
      'd': 'text-red-600 dark:text-red-400',
      'c': 'text-gray-900 dark:text-gray-100'
    };

    return (
      <div className="inline-flex items-center justify-center w-12 h-16 bg-white dark:bg-gray-100 border-2 border-gray-300 dark:border-gray-400 rounded shadow-md mx-1">
        <div className="text-center">
          <div className={`text-xl font-bold ${suitColors[suit] || ''}`}>
            {rank}
          </div>
          <div className={`text-2xl ${suitColors[suit] || ''}`}>
            {suitSymbols[suit] || suit}
          </div>
        </div>
      </div>
    );
  };

  const renderBoard = (board: string) => {
    if (!board) return null;

    // Board format: "AsKhQd" or "As Kh Qd"
    const cards = board.replace(/\s/g, '').match(/.{1,2}/g) || [];

    return (
      <div className="flex justify-center items-center space-x-2 my-6">
        {cards.map((card, idx) => (
          <div key={idx}>
            {renderCard(card)}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="card space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary">
            Hand Replayer
          </h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
            Hand ID: {hand.hand_id}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            {hand.villain_name} vs Hero
          </p>
          <p className="text-lg font-bold text-primary-600 dark:text-primary-400">
            Pot: {hand.pot_bb.toFixed(2)} BB
          </p>
        </div>
      </div>

      {/* Current Street Indicator */}
      <div className="flex justify-center space-x-2">
        {streets.map((street) => (
          <div
            key={street.name}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
              street.name === currentStreet?.name
                ? 'bg-primary-600 dark:bg-primary-500 text-white'
                : 'bg-gray-100 dark:bg-dark-bg-tertiary text-gray-600 dark:text-dark-text-secondary'
            }`}
          >
            {street.name}
          </div>
        ))}
      </div>

      {/* Board Cards */}
      {currentStreet?.board && (
        <div className="bg-poker-felt dark:bg-poker-green rounded-lg p-8">
          <div className="text-center text-white dark:text-gray-200 text-sm font-medium mb-2">
            BOARD
          </div>
          {renderBoard(currentStreet.board)}
        </div>
      )}

      {/* Player Positions */}
      <div className="grid grid-cols-2 gap-6 mt-8">
        {/* Villain */}
        <div className="card !bg-gray-50 dark:!bg-dark-bg-tertiary">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 mb-3">
              <span className="text-2xl">👤</span>
            </div>
            <p className="font-bold text-gray-900 dark:text-dark-text-primary">
              {hand.villain_name}
            </p>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
              Position: {hand.villain_position}
            </p>
            {hand.villain_stack_bb && (
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
                Stack: {hand.villain_stack_bb.toFixed(2)} BB
              </p>
            )}
          </div>
        </div>

        {/* Hero */}
        <div className="card !bg-gray-50 dark:!bg-dark-bg-tertiary">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 mb-3">
              <span className="text-2xl">🎯</span>
            </div>
            <p className="font-bold text-gray-900 dark:text-dark-text-primary">
              Hero
            </p>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
              Position: {hand.hero_position}
            </p>
            {hand.hero_stack_bb && (
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
                Stack: {hand.hero_stack_bb.toFixed(2)} BB
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Actions Timeline */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-dark-bg-tertiary">
        <h4 className="font-semibold text-gray-900 dark:text-dark-text-primary mb-3">
          Action History
        </h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {streets.map((street, streetIdx) => (
            <div key={streetIdx} className="space-y-1">
              <div className="font-medium text-sm text-primary-600 dark:text-primary-400">
                {street.name}
              </div>
              {street.actions.map((action, actionIdx) => (
                <div
                  key={`${streetIdx}-${actionIdx}`}
                  className={`text-sm pl-4 py-1 rounded ${
                    actionIdx <= currentActionIndex
                      ? 'text-gray-900 dark:text-dark-text-primary bg-white dark:bg-dark-bg-secondary'
                      : 'text-gray-400 dark:text-gray-600'
                  }`}
                >
                  {action}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Decision Point Highlight */}
      {hand.street && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-yellow-400 dark:bg-yellow-600 flex items-center justify-center">
                <span className="text-white font-bold">!</span>
              </div>
            </div>
            <div className="flex-1">
              <h5 className="font-semibold text-gray-900 dark:text-dark-text-primary">
                Decision Point: {hand.street.toUpperCase()}
              </h5>
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                <span className="font-medium">{hand.villain_name}</span> action:{' '}
                <span className="font-bold text-primary-600 dark:text-primary-400">
                  {hand.villain_action}
                </span>
              </p>
              {hand.villain_bet_size_bb && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Bet size: {hand.villain_bet_size_bb.toFixed(2)} BB
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Playback Controls */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex items-center justify-center space-x-2">
          <button
            onClick={handleFirst}
            disabled={currentActionIndex === 0}
            className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg-tertiary hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="First action"
          >
            <SkipBack className="w-5 h-5 text-gray-700 dark:text-dark-text-primary" />
          </button>

          <button
            onClick={handlePrev}
            disabled={currentActionIndex === 0}
            className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg-tertiary hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Previous action"
          >
            <ChevronLeft className="w-5 h-5 text-gray-700 dark:text-dark-text-primary" />
          </button>

          <button
            onClick={togglePlayPause}
            className="p-3 rounded-lg bg-primary-600 dark:bg-primary-500 hover:bg-primary-700 dark:hover:bg-primary-600 text-white transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-6 h-6" />
            ) : (
              <Play className="w-6 h-6" />
            )}
          </button>

          <button
            onClick={handleNext}
            disabled={currentActionIndex >= totalActions - 1}
            className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg-tertiary hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Next action"
          >
            <ChevronRight className="w-5 h-5 text-gray-700 dark:text-dark-text-primary" />
          </button>

          <button
            onClick={handleLast}
            disabled={currentActionIndex >= totalActions - 1}
            className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg-tertiary hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Last action"
          >
            <SkipForward className="w-5 h-5 text-gray-700 dark:text-dark-text-primary" />
          </button>
        </div>

        <div className="text-center mt-3">
          <span className="text-sm text-gray-600 dark:text-dark-text-secondary">
            Action {currentActionIndex + 1} of {totalActions}
          </span>
        </div>
      </div>
    </div>
  );
}
