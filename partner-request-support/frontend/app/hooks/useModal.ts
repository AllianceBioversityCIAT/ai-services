'use client';

import { useState } from 'react';
import { Partner, ModalType } from '../types/partner.types';

export const useModal = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<ModalType | null>(null);
  const [selectedPartner, setSelectedPartner] = useState<Partner | null>(null);

  const openModal = (type: ModalType, partner: Partner) => {
    setModalType(type);
    setSelectedPartner(partner);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setModalType(null);
    setSelectedPartner(null);
  };

  return {
    modalOpen,
    modalType,
    selectedPartner,
    openModal,
    closeModal,
    setSelectedPartner,
  };
};
