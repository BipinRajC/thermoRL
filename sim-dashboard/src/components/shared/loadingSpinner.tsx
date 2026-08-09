import { Triangle } from "react-loader-spinner";

export function LoadingSpinner() {
  return (
    <div className="flex justify-center items-center flex-1">
      <Triangle height="120" width="120" color="rgb(59 130 246)" />
    </div>
  );
}
