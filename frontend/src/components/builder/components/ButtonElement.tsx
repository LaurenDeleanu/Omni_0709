"use client";

import React from "react";
import { useNode } from "@craftjs/core";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ButtonElementProps {
  text: string;
}

export const ButtonElement = ({ text }: ButtonElementProps) => {
  const { connectors: { connect, drag } } = useNode();

  return (
    <div ref={(ref: any) => connect(drag(ref))}>
      <Button>{text}</Button>
    </div>
  );
};

const ButtonSettings = () => {
  const { actions: { setProp }, text } = useNode((node) => ({
    text: node.data.props.text
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Texto del botón</Label>
        <Input 
          defaultValue={text} 
          onChange={(e) => setProp((props: any) => props.text = e.target.value)} 
        />
      </div>
    </div>
  );
};

ButtonElement.craft = {
  props: {
    text: "Click Me"
  },
  related: {
    settings: ButtonSettings
  }
};
