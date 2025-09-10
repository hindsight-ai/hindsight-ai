import React, { useState, useEffect, useRef, useCallback } from 'react';

interface RangeSliderProps {
  min: number;
  max: number;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  label: string;
  step?: number;
}

const RangeSlider: React.FC<RangeSliderProps> = ({ min, max, value, onChange, label, step = 1 }) => {
  const [minValue, setMinValue] = useState<number>(value[0]);
  const [maxValue, setMaxValue] = useState<number>(value[1]);
  const minThumbRef = useRef<HTMLInputElement | null>(null);
  const maxThumbRef = useRef<HTMLInputElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [isDraggingMin, setIsDraggingMin] = useState<boolean>(false);
  const [isDraggingMax, setIsDraggingMax] = useState<boolean>(false);

  useEffect(() => {
    setMinValue(value[0]);
    setMaxValue(value[1]);
  }, [value]);

  const calculateValueFromMouseEvent = useCallback((event: MouseEvent, isMinThumb: boolean): number | undefined => {
    if (!trackRef.current) return;

    const trackRect = trackRef.current.getBoundingClientRect();
    const clientX = event.clientX;
    const percentage = Math.max(0, Math.min(1, (clientX - trackRect.left) / trackRect.width));
    let newValue = min + percentage * (max - min);

    // Snap to step
    newValue = Math.round(newValue / step) * step;
    newValue = Math.max(min, Math.min(max, newValue));

    if (isMinThumb) {
      return Math.min(newValue, maxValue - step);
    } else {
      return Math.max(newValue, minValue + step);
    }
  }, [min, max, step, minValue, maxValue]);

  const handleMouseMove = useCallback((event: MouseEvent) => {
    if (isDraggingMin) {
      const newMin = calculateValueFromMouseEvent(event, true);
      if (newMin !== undefined && newMin !== minValue) {
        setMinValue(newMin);
      }
    } else if (isDraggingMax) {
      const newMax = calculateValueFromMouseEvent(event, false);
      if (newMax !== undefined && newMax !== maxValue) {
        setMaxValue(newMax);
      }
    }
  }, [isDraggingMin, isDraggingMax, minValue, maxValue, calculateValueFromMouseEvent]);

  const handleMouseUp = useCallback(() => {
    setIsDraggingMin(false);
    setIsDraggingMax(false);
    onChange([minValue, maxValue]); // Only call onChange when mouse is released
  }, [minValue, maxValue, onChange]);

  useEffect(() => {
    if (isDraggingMin || isDraggingMax) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingMin, isDraggingMax, handleMouseMove, handleMouseUp]);

  const handleMinMouseDown = () => {
    setIsDraggingMin(true);
  };

  const handleMaxMouseDown = () => {
    setIsDraggingMax(true);
  };

  const getBackgroundSize = () => {
    const range = max - min;
    const minPercent = ((minValue - min) / range) * 100;
    const maxPercent = ((maxValue - min) / range) * 100;
    return `${minPercent}% ${100 - maxPercent}%`;
  };

  return (
    <div className="range-slider-container">
      <label>{label}</label>
      <div className="slider-track-wrapper" ref={trackRef}>
        <input
          type="range"
          min={min}
          max={max}
          value={minValue}
          onChange={() => {}} // Controlled component, value updated by mouse events
          onMouseDown={handleMinMouseDown}
          className="thumb thumb--left"
          style={{ backgroundSize: getBackgroundSize() }}
          ref={minThumbRef}
          step={step}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={maxValue}
          onChange={() => {}} // Controlled component, value updated by mouse events
          onMouseDown={handleMaxMouseDown}
          className="thumb thumb--right"
          style={{ backgroundSize: getBackgroundSize() }}
          ref={maxThumbRef}
          step={step}
        />
        <div className="slider-values">
          <span>{minValue}</span> - <span>{maxValue}</span>
        </div>
      </div>
    </div>
  );
};

export default RangeSlider;
